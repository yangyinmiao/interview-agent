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

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || JSON.stringify(err);
      } catch {}
      throw new Error(detail);
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

  async deleteResume(resumeId: string) {
    return this.request(`/resumes/${resumeId}`, {
      method: "DELETE",
    });
  }

  // JDs
  async uploadJD(file: File, title?: string, company?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (company) formData.append("company", company);
    return this.request("/jds/upload", {
      method: "POST",
      body: formData,
    });
  }

  async createJD(data: { title: string; company?: string; description: string }) {
    return this.request("/jds", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getJDs() {
    return this.request("/jds");
  }

  async getJDAnalysis(jdId: string) {
    return this.request(`/jds/${jdId}/analysis`);
  }

  async deleteJD(jdId: string) {
    return this.request(`/jds/${jdId}`, {
      method: "DELETE",
    });
  }

  // Question Banks
  async createQuestionBank(name: string, files?: File[]) {
    const formData = new FormData();
    formData.append("name", name);
    if (files) {
      for (const file of files) {
        formData.append("files", file);
      }
    }
    return this.request("/question-banks", {
      method: "POST",
      body: formData,
    });
  }

  async addFilesToBank(bankId: string, files: File[]) {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    return this.request(`/question-banks/${bankId}/add-files`, {
      method: "POST",
      body: formData,
    });
  }

  async getQuestionBanks() {
    return this.request("/question-banks");
  }

  async deleteQuestionBank(bankId: string) {
    return this.request(`/question-banks/${bankId}`, {
      method: "DELETE",
    });
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

  /** Stream question via SSE. Returns an async generator of events. */
  async *respondStream(interviewId: string, answer: string): AsyncGenerator<{
    type: string; content: string; score?: number; feedback?: string; round_count?: number;
  }> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/interviews/${interviewId}/respond-stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({ answer }),
      credentials: "include",
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { const err = await res.json(); detail = err.detail || JSON.stringify(err); } catch {}
      throw new Error(detail);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {}
        }
      }
    }
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

  async getReferenceAnswer(interviewId: string, messageId: string) {
    return this.request(`/interviews/${interviewId}/messages/${messageId}/reference-answer`, {
      method: "POST",
    });
  }

  async deleteInterview(interviewId: string) {
    return this.request(`/interviews/${interviewId}`, {
      method: "DELETE",
    });
  }

  async deleteInterviews(ids: string[]) {
    return this.request("/interviews/batch", {
      method: "DELETE",
      body: JSON.stringify({ ids }),
    });
  }

  async getInterviews() {
    return this.request("/interviews");
  }
}

export const api = new ApiClient();
