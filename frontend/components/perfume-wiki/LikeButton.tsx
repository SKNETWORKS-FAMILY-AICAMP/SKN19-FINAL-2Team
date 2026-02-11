"use client";

/**
 * 좋아요 버튼 컴포넌트
 * 사용자가 에피소드에 좋아요를 표시할 수 있는 인터랙티브 버튼
 */
import { useState } from "react";

type LikeButtonProps = {
  initialLikes?: number; // 초기 좋아요 수
};

export default function LikeButton({ initialLikes = 2 }: LikeButtonProps) {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(initialLikes);

  const handleLike = () => {
    // 좋아요 토글 및 카운트 업데이트
    setLikeCount((prev) => (liked ? prev - 1 : prev + 1));
    setLiked(!liked);
  };

  return (
    <button
      type="button"
      onClick={handleLike}
      className="flex items-center gap-2.5 px-5 py-2.5 rounded-full border border-[#EFEFEF] bg-white hover:border-[#C8A24D] hover:shadow-md transition-all duration-300"
      aria-label={liked ? "좋아요 취소" : "좋아요"}
    >
      <span className={`text-xl transition-colors ${liked ? "text-[#C8A24D]" : "text-[#CCC]"}`}>
        {liked ? "♥" : "♡"}
      </span>
      <span className="text-sm font-semibold text-[#555]">{likeCount}</span>
    </button>
  );
}
