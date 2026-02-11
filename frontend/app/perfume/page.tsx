"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import PageLayout from "@/components/common/PageLayout";

import type { PerfumeDetail, RatioItem } from "./types";

const API_URL = "/api";

const ACCORD_COLORS = [
  "#e91e63",
  "#3498db",
  "#2ecc71",
  "#f39c12",
  "#8e44ad",
];

const PLACEHOLDER_IMAGE =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'><rect width='100%25' height='100%25' fill='%23f4f6f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999' font-size='20'>No Image</text></svg>";

function formatRatio(item: RatioItem) {
  return `${item.ratio}%`;
}

function joinNames(items: RatioItem[]) {
  return items.map((item) => item.name).join(", ");
}

function PerfumeDetailContent() {
  const searchParams = useSearchParams();
  const perfumeId = useMemo(() => {
    const id = searchParams.get("id") || searchParams.get("perfume_id");
    return id ? Number(id) : null;
  }, [searchParams]);

  const [detail, setDetail] = useState<PerfumeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!perfumeId || Number.isNaN(perfumeId)) {
      setError("향수 ID가 필요합니다.");
      return;
    }

    let cancelled = false;

    const fetchDetail = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${API_URL}/perfumes/detail?perfume_id=${perfumeId}`);
        if (!res.ok) {
          throw new Error(`API error: ${res.status}`);
        }
        const data = (await res.json()) as PerfumeDetail;
        if (!cancelled) {
          setDetail(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError("향수 정보를 불러오지 못했습니다.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [perfumeId]);

  const hasNotes = detail && (detail.notes.top.length || detail.notes.middle.length || detail.notes.base.length);
  const hasAccords = detail && detail.accords.length > 0;
  const hasSeasons = detail && detail.seasons.length > 0;
  const hasOccasions = detail && detail.occasions.length > 0;

  return (
    <PageLayout subTitle="Perfume Detail">
      <div className="page pt-24">
        <div className="container">
          {loading && <div className="status">불러오는 중...</div>}
          {!loading && error && <div className="status error">{error}</div>}

          {!loading && !error && detail && (
            <>
              <header>
                <div>
                  <div className="brand">{detail.brand || "정보 없음"}</div>
                  <h1>{detail.name || "향수 정보 없음"}</h1>
                </div>
              </header>

              <div className="wiki-layout">
                <div className="main-content">
                  <div className="hero-image-container">
                    <div className="hero-image-crop">
                      <img
                        src={detail.image_url || PLACEHOLDER_IMAGE}
                        alt={detail.name}
                      />
                    </div>
                  </div>

                  {hasNotes ? (
                    <>
                      <h2>향의 구조 (Notes)</h2>
                      <div className="note-container">
                        <div className="note-level top-note">
                          <span className="note-label">Top Notes</span>
                          {detail.notes.top.length ? detail.notes.top.join(", ") : "정보 없음"}
                        </div>
                        <div className="note-level mid-note">
                          <span className="note-label">Middle Notes</span>
                          {detail.notes.middle.length ? detail.notes.middle.join(", ") : "정보 없음"}
                        </div>
                        <div className="note-level base-note">
                          <span className="note-label">Base Notes</span>
                          {detail.notes.base.length ? detail.notes.base.join(", ") : "정보 없음"}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="empty-section">노트 정보가 없습니다.</div>
                  )}

                  {hasAccords && (
                    <>
                      <h2>주요 어코드 (Main Accords)</h2>
                      <div className="accord-list">
                        {detail.accords.map((accord, index) => (
                          <div key={`${accord.name}-${index}`} className="accord-item">
                            <div className="accord-label">
                              <span>{accord.name}</span>
                              <span>{formatRatio(accord)}</span>
                            </div>
                            <div className="progress-bg">
                              <div
                                className="progress-fill"
                                style={{
                                  width: `${accord.ratio}%`,
                                  backgroundColor: ACCORD_COLORS[index % ACCORD_COLORS.length],
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {(hasSeasons || hasOccasions) && (
                    <>
                      <h2>스타일 & 추천 (Vibe & TPO)</h2>
                      <p>
                        <strong>느낌:</strong>
                        <span className="tag-cloud inline">
                          {detail.accords.length
                            ? detail.accords.map((accord, index) => (
                              <span key={`${accord.name}-${index}`} className="tag">#{accord.name}</span>
                            ))
                            : "정보 없음"}
                        </span>
                      </p>
                      <p>
                        <strong>추천 계절:</strong>{" "}
                        {hasSeasons ? (
                          detail.seasons.map((season, index) => (
                            <span key={`${season.name}-${index}`} className="season-tag">
                              {season.name} ({formatRatio(season)}){index < detail.seasons.length - 1 ? ", " : ""}
                            </span>
                          ))
                        ) : (
                          "정보 없음"
                        )}
                      </p>
                      <p>
                        <strong>추천 상황:</strong>{" "}
                        {hasOccasions ? joinNames(detail.occasions) : "정보 없음"}
                      </p>
                    </>
                  )}
                </div>

                <div className="side-panel">
                  <div className="infobox">
                    <table className="info-table">
                      <tbody>
                        <tr>
                          <th>브랜드</th>
                          <td>{detail.brand || "정보 없음"}</td>
                        </tr>
                        <tr>
                          <th>출시 연도</th>
                          <td>{detail.release_year ?? "정보 없음"}</td>
                        </tr>
                        <tr>
                          <th>농도</th>
                          <td>{detail.concentration || "정보 없음"}</td>
                        </tr>
                        <tr>
                          <th>조향사</th>
                          <td>{detail.perfumer || "정보 없음"}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>


        <style jsx>{`
        :global(body) {
          margin: 0;
          background-color: #f4f6f7;
          color: #333;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        }

        .page {
          min-height: 100vh;
          padding: 20px;
        }

        .container {
          max-width: 1000px;
          margin: 0 auto;
          background-color: #ffffff;
          padding: 40px;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        header {
          border-bottom: 2px solid #eee;
          padding-bottom: 20px;
          margin-bottom: 30px;
          display: flex;
          justify-content: space-between;
          align-items: end;
        }

        h1 {
          margin: 0;
          font-size: 2.5rem;
          color: #2c3e50;
        }

        .brand {
          font-size: 1.2rem;
          color: #7f8c8d;
          font-weight: 500;
        }

        .wiki-layout {
          display: flex;
          gap: 40px;
          flex-wrap: wrap;
        }

        .main-content {
          flex: 2;
          min-width: 300px;
        }

        .side-panel {
          flex: 1;
          min-width: 250px;
        }

        .infobox {
          background: #f8f9fa;
          border: 1px solid #ddd;
          padding: 20px;
          border-radius: 8px;
        }

        .info-table {
          width: 100%;
          border-collapse: collapse;
        }

        .info-table th {
          text-align: left;
          color: #7f8c8d;
          padding: 8px 0;
          width: 40%;
        }

        .info-table td {
          font-weight: 600;
          padding: 8px 0;
        }

        h2 {
          border-left: 5px solid #2c3e50;
          padding-left: 10px;
          margin-top: 40px;
          margin-bottom: 20px;
          font-size: 1.5rem;
        }

        .note-container {
          display: flex;
          flex-direction: column;
          gap: 10px;
          text-align: center;
        }

        .note-level {
          padding: 15px;
          border-radius: 8px;
          font-weight: 500;
        }

        .top-note {
          background-color: #e8f8f5;
          border: 1px solid #d1f2eb;
        }

        .mid-note {
          background-color: #fef9e7;
          border: 1px solid #f9e79f;
        }

        .base-note {
          background-color: #f4f6f6;
          border: 1px solid #d5dbdb;
        }

        .note-label {
          display: block;
          font-size: 0.8rem;
          color: #7f8c8d;
          margin-bottom: 5px;
          text-transform: uppercase;
        }

        .accord-item {
          margin-bottom: 12px;
        }

        .accord-label {
          display: flex;
          justify-content: space-between;
          margin-bottom: 4px;
          font-size: 0.9rem;
        }

        .progress-bg {
          background-color: #eee;
          height: 10px;
          border-radius: 5px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          border-radius: 5px;
        }

        .tag-cloud {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-left: 8px;
        }

        .tag-cloud.inline {
          display: inline-flex;
        }

        .tag {
          background-color: #e9ecef;
          padding: 5px 12px;
          border-radius: 20px;
          font-size: 0.9rem;
          color: #495057;
        }

        .season-tag {
          font-weight: bold;
          color: #d35400;
        }

        .hero-image-container {
          display: flex;
          justify-content: center;
          margin-bottom: 20px;
        }

        .hero-image-crop {
          width: 250px;
          height: 250px;
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        .hero-image-crop img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center;
        }

        .status {
          padding: 16px;
          border-radius: 8px;
          background: #f8f9fa;
          color: #666;
          margin-bottom: 24px;
        }

        .status.error {
          background: #fff1f2;
          color: #b91c1c;
        }

        .empty-section {
          padding: 16px;
          border-radius: 8px;
          background: #f8f9fa;
          color: #666;
          margin-top: 16px;
        }

        @media (max-width: 768px) {
          .wiki-layout {
            flex-direction: column-reverse;
          }

          .side-panel {
            width: 100%;
          }
        }
      `}</style>
    </div>
    </PageLayout>
  );
}

export default function PerfumeDetailPage() {
  return (
    <Suspense fallback={<div className="page"><div className="container"><div className="status">로딩 중...</div></div></div>}>
      <PerfumeDetailContent />
    </Suspense>
  );
}
