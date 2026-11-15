"use client";
import { useState, FormEvent } from "react";

export default function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed");
      setStatus("done");
      setMsg(data.already ? "You're already subscribed!" : "You're in! We'll notify you of new models and datasets.");
      setEmail("");
    } catch {
      setStatus("error");
      setMsg("Something went wrong. Please try again.");
    }
  }

  return (
    <section className="subscribe-section">
      <div className="wrap">
        <div className="subscribe-inner">
          <div className="subscribe-copy">
            <p className="sec-label">Stay in the loop</p>
            <h2>Get notified of updates</h2>
            <p className="subscribe-lede">
              New health models, datasets, and leaderboard scores — delivered to your inbox weekly. No spam.
            </p>
          </div>
          <div className="subscribe-form-wrap">
            {status === "done" ? (
              <p className="subscribe-success">{msg}</p>
            ) : (
              <form className="subscribe-form" onSubmit={handleSubmit}>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={status === "loading"}
                  aria-label="Email address"
                />
                <button
                  type="submit"
                  className="btn primary"
                  disabled={status === "loading"}
                >
                  {status === "loading" ? "Subscribing…" : "Subscribe"}
                </button>
                {status === "error" && (
                  <p className="subscribe-error">{msg}</p>
                )}
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
