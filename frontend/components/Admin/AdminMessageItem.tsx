"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type Message = {
    role: "user" | "assistant";
    text: string;
    isStreaming?: boolean;
};

// [Admin 전용] 텍스트 파서 & 마크다운 스타일링
// 불필요한 저장 버튼 로직 제거하고 스타일링에 집중
const parseMessageContent = (text: string) => {
    if (!text) return null;

    // [Note] 저장 버튼 태그가 오더라도 관리자 화면에서는 렌더링하지 않음 (단순 텍스트 처리)
    // 혹은 정규식으로 제거하거나 무시

    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                a: ({ node, ...props }: any) => (
                    <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-600 hover:underline" />
                ),
                img: ({ node, ...props }: any) => {
                    return (
                        <span className="mx-auto my-6 block h-40 w-40 md:h-[200px] md:w-[200px] overflow-hidden rounded-2xl shadow-lg border border-slate-200 relative bg-white">
                            <img
                                {...props}
                                className="h-full w-full object-contain p-2"
                                alt={props.alt || "Perfume Image"}
                            />
                        </span>
                    );
                },
                h2: ({ node, ...props }: any) => (
                    <h2 {...props} className="text-lg font-bold mt-6 mb-3 text-[#393939] border-l-4 border-pink-500 pl-3 leading-none" />
                ),
                h3: ({ node, ...props }: any) => (
                    <h3 {...props} className="text-base font-bold mt-6 mb-2 text-slate-800 border-b-2 border-slate-100 pb-1" />
                ),
                hr: ({ node, ...props }: any) => <hr {...props} className="my-8 border-[#E5E4DE]" />,
                em: ({ node, ...props }: any) => (
                    <em {...props} className="not-italic text-violet-600 font-bold mr-1" />
                ),
                strong: ({ node, ...props }: any) => <strong {...props} className="text-pink-600 font-extrabold" />,
                p: ({ node, ...props }: any) => <p {...props} className="mb-3 last:mb-0 leading-relaxed text-slate-700" />,
                ul: ({ node, ...props }: any) => <ul {...props} className="list-disc pl-5 mb-4 space-y-1 text-sm" />,
                li: ({ node, ...props }: any) => <li {...props} className="pl-1" />,
                blockquote: ({ node, ...props }: any) => (
                    <blockquote
                        {...props}
                        className="my-3 pl-4 border-l-[3px] border-pink-300 text-sm text-slate-600 italic bg-transparent"
                    />
                ),
                table: ({ node, ...props }: any) => (
                    <div className="overflow-x-auto my-4 rounded-lg border border-gray-100">
                        <table {...props} className="w-full text-sm text-left text-gray-600" />
                    </div>
                ),
                thead: ({ node, ...props }: any) => (
                    <thead {...props} className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-100" />
                ),
                tbody: ({ node, ...props }: any) => (
                    <tbody {...props} className="bg-white divide-y divide-gray-50" />
                ),
                tr: ({ node, ...props }: any) => <tr {...props} className="hover:bg-gray-50 transition-colors" />,
                th: ({ node, ...props }: any) => (
                    <th {...props} className="px-4 py-2 font-semibold text-center whitespace-nowrap" />
                ),
                td: ({ node, ...props }: any) => (
                    <td {...props} className="px-4 py-2 text-center whitespace-nowrap" />
                ),
            }}
        >
            {text}
        </ReactMarkdown>
    );
};

const AdminMessageItem = ({ message }: { message: Message }) => {
    if (message.role === "assistant" && !message.text) return null;

    return (
        <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {/* [Admin 전용 설정]
                 - max-w-3xl: 와이드 화면에서도 가독성 확보 (일반 사용자는 max-w-80% 사용)
             */}
            <div className={`max-w-[90%] md:max-w-2xl lg:max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${message.role === "user"
                ? "bg-[#E5E4DE] text-[#393939]"
                : "bg-white text-[#393939] border border-[#E5E4DE]"
                }`}>
                <div className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-[#8E8E8E]">
                    {message.role === "user" ? "나" : "AI"}
                </div>
                {message.role === "assistant" ? (
                    <div className="w-full break-words">
                        {parseMessageContent(message.text)}
                    </div>
                ) : (
                    <div className="whitespace-pre-wrap break-words">{message.text}</div>
                )}
            </div>
        </div>
    );
};

export default AdminMessageItem;
