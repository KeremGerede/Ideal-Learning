// src/components/AITutorChat.jsx

import { useState, useEffect, useRef } from "react";
import { getChatMessages, askAITutor } from "../api/apiClient";

function AITutorChat({ plan, weeks, openWeekIds }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [error, setError] = useState("");
    
    // Aktif hafta bağlamı. Sync with parent, but can also be manually overridden.
    const [selectedWeekId, setSelectedWeekId] = useState(null);

    const messagesEndRef = useRef(null);

    // Sync selected week with the open week in parent accordion
    useEffect(() => {
        if (openWeekIds && openWeekIds.length > 0) {
            // Pick the first open week
            setSelectedWeekId(openWeekIds[0]);
        } else {
            // Default to general context if no week is open
            setSelectedWeekId(null);
        }
    }, [openWeekIds]);

    // Load message history on plan/open state changes
    useEffect(() => {
        if (isOpen && plan?.id) {
            loadMessages();
        }
    }, [isOpen, plan?.id]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, loading]);

    async function loadMessages() {
        try {
            setHistoryLoading(true);
            setError("");
            const data = await getChatMessages(plan.id);
            setMessages(data);
        } catch (err) {
            console.error("Sohbet geçmişi yüklenemedi:", err);
            setError("Sohbet geçmişi yüklenemedi.");
        } finally {
            setHistoryLoading(false);
        }
    }

    async function handleSendMessage(textToSend) {
        const messageText = textToSend || inputMessage;
        if (!messageText.trim() || loading || !plan?.id) return;

        setInputMessage("");
        setLoading(true);
        setError("");

        // Optimistic UI update: add user message immediately
        const tempUserMessage = {
            id: Date.now(),
            plan_id: plan.id,
            week_id: selectedWeekId,
            sender: "user",
            message: messageText,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, tempUserMessage]);

        try {
            const aiResponse = await askAITutor(plan.id, {
                message: messageText,
                week_id: selectedWeekId
            });
            
            // Replace temporary user message + append AI response
            // We reload messages from DB to get correct IDs/timestamps and prevent misalignment
            await loadMessages();
        } catch (err) {
            setError(err.message || "Mesaj iletilemedi. Lütfen tekrar deneyin.");
            // Remove the optimistic message if it failed
            setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id));
        } finally {
            setLoading(false);
        }
    }

    function handleQuickQuestion(questionText) {
        handleSendMessage(questionText);
    }

    // Markdown ve kod bloklarını şık bir şekilde formatlayan helper
    function renderFormattedMessage(text) {
        if (!text) return null;
        
        // Kod bloklarını (```lang ... ```) ayır
        const parts = text.split(/(```[\s\S]*?```)/g);
        
        return parts.map((part, index) => {
            if (part.startsWith("```") && part.endsWith("```")) {
                const codeContent = part.slice(3, -3).trim();
                const lines = codeContent.split("\n");
                let language = "";
                let code = codeContent;
                
                if (lines.length > 1 && !lines[0].includes(" ") && lines[0].length < 15) {
                    language = lines[0];
                    code = lines.slice(1).join("\n");
                }
                
                return (
                    <div key={index} className="my-3 overflow-hidden rounded-xl border border-slate-800 bg-slate-950 font-mono text-xs">
                        <div className="bg-slate-900/80 px-3 py-1.5 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-800/80 flex justify-between items-center">
                            <span>{language || "code"}</span>
                            <button 
                                onClick={() => navigator.clipboard.writeText(code)}
                                className="hover:text-indigo-400 text-slate-400 font-sans transition-colors cursor-pointer"
                                type="button"
                            >
                                Kopyala
                            </button>
                        </div>
                        <pre className="p-3 overflow-x-auto text-slate-300 leading-relaxed"><code>{code}</code></pre>
                    </div>
                );
            }
            
            // Satır içi kodları (`code`) formatla
            const inlineParts = part.split(/(`[^`\n]+`)/g);
            return (
                <span key={index}>
                    {inlineParts.map((subPart, subIndex) => {
                        if (subPart.startsWith("`") && subPart.endsWith("`")) {
                            return (
                                <code key={subIndex} className="mx-1 rounded bg-slate-900 border border-slate-800 px-1 py-0.5 font-mono text-[13px] text-indigo-300 font-semibold">
                                    {subPart.slice(1, -1)}
                                </code>
                            );
                        }
                        
                        // Kalın yazıları (**bold**) formatla
                        const boldParts = subPart.split(/(\*\*[^*]+\*\*)/g);
                        return boldParts.map((bPart, bIndex) => {
                            if (bPart.startsWith("**") && bPart.endsWith("**")) {
                                return (
                                    <strong key={bIndex} className="font-semibold text-white">
                                        {bPart.slice(2, -2)}
                                    </strong>
                                );
                            }
                            
                            // Liste elemanları ve satır sonları
                            const lines = bPart.split("\n");
                            return lines.map((line, lIndex) => {
                                const isBullet = line.trim().startsWith("- ") || line.trim().startsWith("* ");
                                const cleanLine = isBullet ? line.trim().replace(/^[-*]\s+/, "") : line;
                                
                                if (isBullet) {
                                    return (
                                        <span key={lIndex} className="block pl-4 my-1 relative before:content-['•'] before:absolute before:left-0 before:text-indigo-400">
                                            {cleanLine}
                                        </span>
                                    );
                                }
                                
                                return (
                                    <span key={lIndex}>
                                        {line}
                                        {lIndex < lines.length - 1 && <br />}
                                    </span>
                                );
                            });
                        });
                    })}
                </span>
            );
        });
    }

    // Seçili hafta nesnesini bul
    const currentWeekObj = weeks?.find(w => w.id === selectedWeekId);

    // Quick questions based on active context
    const quickQuestions = selectedWeekId && currentWeekObj
        ? [
            `Hafta ${currentWeekObj.week_number} konusunu özetler misin?`,
            `Hafta ${currentWeekObj.week_number} projesi için ipucu alabilir miyim?`,
            "Bu haftaki görevleri nasıl tamamlamalıyım?",
          ]
        : [
            "Genel olarak öğrenme planımın amacı nedir?",
            "Nereden çalışmaya başlamamı önerirsin?",
            "Bana verimli öğrenme için tavsiyeler ver.",
          ];

    return (
        <>
            {/* Floating Action Button (FAB) */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 transition-transform duration-300 hover:scale-110 active:scale-95 cursor-pointer ${
                    isOpen ? "rotate-90" : ""
                }`}
            >
                {isOpen ? (
                    <span className="text-xl font-semibold">✕</span>
                ) : (
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="h-6 w-6 animate-pulse"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M8.625 9.75a.625.625 0 11-1.25 0 .625.625 0 011.25 0zm4.5 0a.625.625 0 11-1.25 0 .625.625 0 011.25 0zm4.5 0a.625.625 0 11-1.25 0 .625.625 0 011.25 0zM12 3c4.97 0 9 3.03 9 6.75 0 3.515-3.418 6.425-8 6.713-1.004.062-1.92.518-2.67 1.192L7.5 21V16.75c-2.67-.47-4.5-2.73-4.5-5.25C3 6.03 7.03 3 12 3z"
                        />
                    </svg>
                )}
            </button>

            {/* Chatbot Window */}
            {isOpen && (
                <div className="fixed bottom-24 right-6 z-50 flex h-[600px] w-96 max-w-[calc(100vw-2rem)] flex-col rounded-3xl border border-slate-800/80 bg-slate-950/80 backdrop-blur-xl shadow-2xl transition-all duration-300 ease-in-out">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-slate-800/60 p-4 bg-slate-900/40 rounded-t-3xl">
                        <div className="flex items-center gap-3">
                            <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 text-white font-bold shadow-md shadow-indigo-500/20">
                                🤖
                                <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border border-slate-950 bg-emerald-500" />
                            </div>
                            
                            <div>
                                <h5 className="font-bold text-slate-100 text-sm">
                                    Kişisel Eğitmen Asistanı
                                </h5>
                                <p className="text-[10px] text-emerald-400 font-semibold tracking-wide">
                                    Gemini 1.5 Pro · Çevrimiçi
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={() => setIsOpen(false)}
                            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-slate-200 cursor-pointer"
                        >
                            ✕
                        </button>
                    </div>

                    {/* Context Selector */}
                    <div className="border-b border-slate-800/40 bg-slate-950/60 px-4 py-2 flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-400 uppercase tracking-wider text-[9px]">Sohbet Bağlamı:</span>
                        
                        <select
                            value={selectedWeekId || ""}
                            onChange={(e) => setSelectedWeekId(e.target.value ? Number(e.target.value) : null)}
                            className="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-slate-200 text-xs focus:border-indigo-500 outline-none cursor-pointer"
                        >
                            <option value="">🌍 Genel Plan Bağlamı</option>
                            {weeks?.map((w) => (
                                <option key={w.id} value={w.id}>
                                    📅 Hafta {w.week_number}: {w.title.length > 20 ? w.title.slice(0, 20) + "..." : w.title}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Chat Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
                        {error && (
                            <div className="rounded-xl border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-200 text-center">
                                {error}
                            </div>
                        )}

                        {historyLoading && messages.length === 0 ? (
                            <div className="flex h-full items-center justify-center">
                                <span className="text-sm text-slate-400">Geçmiş yükleniyor...</span>
                            </div>
                        ) : messages.length === 0 ? (
                            <div className="flex h-full flex-col items-center justify-center p-6 text-center space-y-3">
                                <div className="text-3xl">👋</div>
                                <h6 className="font-semibold text-slate-200 text-sm">Merhaba! Ben kişisel AI eğitmeniniz.</h6>
                                <p className="text-xs text-slate-400">
                                    Öğrenme planınız, haftalık konularınız, görevleriniz ve mini projeleriniz hakkında her şeyi biliyorum. İstediğinizi sorun!
                                </p>
                            </div>
                        ) : (
                            messages.map((msg) => {
                                const isUser = msg.sender === "user";
                                // Get the week badge if the message had specific week context
                                const msgWeek = weeks?.find(w => w.id === msg.week_id);

                                return (
                                    <div
                                        key={msg.id}
                                        className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-1`}
                                    >
                                        {!isUser && msgWeek && (
                                            <span className="text-[9px] bg-slate-900 border border-slate-800 text-indigo-300 font-semibold px-2 py-0.5 rounded-full ml-1">
                                                📅 Hafta {msgWeek.week_number} Bağlamı
                                            </span>
                                        )}
                                        
                                        <div
                                            className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                                                isUser
                                                    ? "bg-indigo-600/30 text-slate-100 border border-indigo-500/20 rounded-tr-none max-w-[85%]"
                                                    : "bg-slate-900/60 text-slate-200 border border-slate-800/80 rounded-tl-none max-w-[85%]"
                                            }`}
                                        >
                                            {isUser ? msg.message : renderFormattedMessage(msg.message)}
                                        </div>
                                    </div>
                                );
                            })
                        )}

                        {loading && (
                            <div className="flex flex-col items-start space-y-1">
                                <div className="rounded-2xl rounded-tl-none bg-slate-900/60 border border-slate-800/80 px-4 py-3 text-sm text-slate-400 max-w-[85%] flex items-center gap-2">
                                    <span className="flex h-2 w-2 relative">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                                    </span>
                                    Düşünüyor...
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Quick Questions Helper */}
                    <div className="px-4 py-2 border-t border-slate-900/40 bg-slate-950/40">
                        <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                            {quickQuestions.map((q, i) => (
                                <button
                                    key={i}
                                    type="button"
                                    onClick={() => handleQuickQuestion(q)}
                                    disabled={loading}
                                    className="rounded-full border border-indigo-500/10 bg-indigo-500/5 px-2.5 py-1 text-[11px] text-indigo-300 transition hover:bg-indigo-500/15 hover:border-indigo-500/30 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Input Footer */}
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            handleSendMessage();
                        }}
                        className="border-t border-slate-800/60 p-4 bg-slate-900/20 flex gap-2 rounded-b-3xl"
                    >
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            disabled={loading}
                            placeholder="Bir soru yazın..."
                            className="flex-1 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 outline-none transition disabled:opacity-60"
                        />
                        <button
                            type="submit"
                            disabled={loading || !inputMessage.trim()}
                            className="rounded-2xl bg-indigo-500 p-2.5 text-white transition hover:bg-indigo-400 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed cursor-pointer"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2}
                                stroke="currentColor"
                                className="h-5 w-5"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                                />
                            </svg>
                        </button>
                    </form>
                </div>
            )}
        </>
    );
}

export default AITutorChat;
