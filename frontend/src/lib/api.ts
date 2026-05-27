const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem("token");
    }
    return this.token;
  }

  private async request(path: string, options: RequestInit = {}): Promise<any> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      this.setToken(null);
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (res.status === 204) {
      return null;
    }

    return res.json();
  }

  // Auth
  async register(name: string, email: string, password: string) {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  }

  async login(email: string, password: string) {
    return this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  // Resumes
  async uploadResume(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("/resumes/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getResumes() {
    return this.request("/resumes");
  }

  async getResumeAnalysis(resumeId: string) {
    return this.request(`/resumes/${resumeId}/analysis`);
  }

  // JDs
  async uploadJD(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("/jds/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getJDs() {
    return this.request("/jds");
  }

  async getJDAnalysis(jdId: string) {
    return this.request(`/jds/${jdId}/analysis`);
  }

  // Question Banks
  async uploadQuestionBank(file: File, name?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (name) {
      formData.append("name", name);
    }
    return this.request("/question-banks/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getQuestionBanks() {
    return this.request("/question-banks");
  }

  // Interviews
  async createInterview(data: {
    resume_id?: string;
    jd_id?: string;
    question_bank_id?: string;
    mode: string;
    max_rounds?: number;
  }) {
    return this.request("/interviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async startInterview(interviewId: string) {
    return this.request(`/interviews/${interviewId}/start`, {
      method: "POST",
    });
  }

  async respondToQuestion(interviewId: string, answer: string) {
    return this.request(`/interviews/${interviewId}/respond`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    });
  }

  async getInterviewMessages(interviewId: string) {
    return this.request(`/interviews/${interviewId}/messages`);
  }

  async endInterview(interviewId: string) {
    return this.request(`/interviews/${interviewId}/end`, {
      method: "POST",
    });
  }

  async getInterviewReport(interviewId: string) {
    return this.request(`/interviews/${interviewId}/report`);
  }

  async getInterviews() {
    return this.request("/interviews");
  }
}

export const api = new ApiClient();
