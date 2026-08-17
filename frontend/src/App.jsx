import { useEffect, useRef, useState } from "react";
import "./App.css";


function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef(null);


  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);


  const askQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || loading) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ]);

    setQuestion("");
    setLoading(true);

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

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer || "",
        sources: data.cited_sources || [],
      };

      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ]);
    } catch (err) {
      console.error(err);

      const errorMessage = {
        id: crypto.randomUUID(),
        role: "error",
        content:
          "暂时无法连接 AI 辅导员，请确认后端服务已经启动。",
      };

      setMessages((currentMessages) => [
        ...currentMessages,
        errorMessage,
      ]);
    } finally {
      setLoading(false);
    }
  };


  const handleSubmit = (event) => {
    event.preventDefault();
    askQuestion();
  };


  const handleKeyDown = (event) => {
    if (
      event.key === "Enter"
      && !event.shiftKey
    ) {
      event.preventDefault();
      askQuestion();
    }
  };


  return (
    <div className="app">
      <div className="chat-container">
        <header className="header">
          <div className="header-text">
            <h1>AI 辅导员</h1>
            <p>基于学生手册的政策问答助手</p >
          </div>

          {messages.length > 0 && (
            <button
              className="clear-button"
               type="button"
               onClick={() => setMessages([])}
               disabled={loading}
            >
             清空对话
            </button>
          )}
        </header>

        <main className="content">
          {messages.length === 0 && !loading && (
            <div className="welcome">
              <h2>你好，有什么可以帮你？</h2>

              <p>
                可以询问请假、学籍、选课、
                奖学金等学生手册相关问题。
              </p >
            </div>
          )}

          <div className="messages">
            {messages.map((message) => {
              if (message.role === "user") {
                return (
                  <div
                    className="message-row user-row"
                    key={message.id}
                  >
                    <div className="user-message">
                      {message.content}
                    </div>
                  </div>
                );
              }

              if (message.role === "error") {
                return (
                  <div
                    className="error"
                    key={message.id}
                  >
                    {message.content}
                  </div>
                );
              }

              return (
                <div
                  className="message-row assistant-row"
                  key={message.id}
                >
                  <div className="answer-card">
                    <div className="assistant-label">
                      AI 辅导员
                    </div>

                    <div className="answer-text">
                      {message.content}
                    </div>

                    {message.sources?.length > 0 && (
                      <div className="sources">
                        <h3>政策依据</h3>

                        {message.sources.map(
                          (source) => (
                            <div
                              className="source-card"
                              key={
                                source.source_id
                              }
                            >
                              <strong>
                                {
                                  source.document_title
                                }
                              </strong>

                              <p>
                                {source.chapter ||
                                  "未标注章节"}
                                {" · "}
                                {source.article ||
                                  "未标注条款"}
                              </p >

                              {source.pdf_pages
                                ?.length > 0 && (
                                <p>
                                  PDF 第
                                  {source.pdf_pages.join(
                                    "、"
                                  )}
                                  页
                                </p >
                              )}
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="message-row assistant-row">
                <div className="loading-message">
                  <span className="loading-dot"></span>
                  <span className="loading-dot"></span>
                  <span className="loading-dot"></span>

                  <span className="loading-text">
                    正在查询学生手册...
                  </span>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
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
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题..."
            rows="3"
            disabled={loading}
          />

          <button
            type="submit"
            disabled={
              loading || !question.trim()
            }
          >
            {loading ? "回答中..." : "发送"}
          </button>
        </form>

        <div className="input-hint">
          Enter 发送 · Shift + Enter 换行
        </div>
      </div>
    </div>
  );
}


export default App;