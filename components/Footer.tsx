export default function Footer() {
  return (
    <footer>
      <div className="wrap foot">
        <p>
          <strong>HealthLLM</strong> — open benchmarks for health AI.
          Scores use temperature 0, seed 42, 100 samples per eval. Results may vary across hardware and Ollama versions.
        </p>
        <p>
          <strong>Not medical advice.</strong> These benchmarks measure language model performance, not clinical safety.
          Always validate models with domain experts before clinical use.
        </p>
        <p style={{ marginTop: 16 }}>
          <a href="https://github.com/devankit01/healthllm" target="_blank" rel="noopener noreferrer">GitHub</a>
          {" · "}
          <a href="https://github.com/devankit01/healthllm/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener noreferrer">Contributing</a>
          {" · "}
          <a href="https://github.com/devankit01/healthllm/issues" target="_blank" rel="noopener noreferrer">Issues</a>
        </p>
      </div>
    </footer>
  );
}
