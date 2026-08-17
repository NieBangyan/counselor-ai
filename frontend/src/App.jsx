import { useState } from "react";
import "./App.css";


function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  const askQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || loading) {
      return;
    }

    setLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: trimmedQuestion,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `请求失败：${response.status}`
        );
      }

      const data = await response.json();

      setAnswer(data.answer || "");
      setSources(data.cited_sources || []);
    } catch (err) {
      setError(
        "暂时无法连接 AI 辅导员，请确认后端服务已经启动。"
      );

      console.error(err);
    } finally {
      setLoading(false);
    }
  };


  const handleSubmit = (event) => {
    event.preventDefault();
    askQuestion();
  };


  return (
    <div className="app">
      <div className="chat-container">
        <header className="header">
          <h1>AI 辅导员</h1>
          <p>基于学生手册的政策问答助手</p >
        </header>

        <main className="content">
          {!answer && !loading && !error && (
            <div className="welcome">
              <h2>你好，有什么可以帮你？</h2>
              <p>
                可以询问请假、学籍、选课、
                奖学金等学生手册相关问题。
              </p >
            </div>
          )}

          {loading && (
            <div className="status">
              正在查询学生手册并生成回答...
            </div>
          )}

          {error && (
            <div className="error">
              {error}
            </div>
          )}

          {answer && (
            <div className="answer-card">
              <h2>回答</h2>

              <div className="answer-text">
                {answer}
              </div>

              {sources.length > 0 && (
                <div className="sources">
                  <h3>政策依据</h3>

                  {sources.map((source) => (
                    <div
                      className="source-card"
                      key={source.source_id}
                    >
                      <strong>
                        {source.document_title}
                      </strong>

                      <p>
                        {source.chapter || "未标注章节"}
                        {" · "}
                        {source.article || "未标注条款"}
                      </p >

                      {source.pdf_pages?.length > 0 && (
                        <p>
                          PDF 第
                          {source.pdf_pages.join("、")}
                          页
                        </p >
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>

        <form
          className="input-area"
          onSubmit={handleSubmit}
        >
          <textarea
            value={question}
            onChange={(event) =>
              setQuestion(event.target.value)
            }
            placeholder="例如：我想请四天假，需要谁批准？"
            rows="3"
            disabled={loading}
          />

          <button
            type="submit"
            disabled={
              loading || !question.trim()
            }
          >
            {loading ? "正在回答..." : "发送"}
          </button>
        </form>
      </div>
    </div>
  );
}


export default App;