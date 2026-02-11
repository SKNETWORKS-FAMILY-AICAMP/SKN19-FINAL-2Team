import React from 'react';
import { Sparkles } from "lucide-react";
import { ACCORD_COLORS, ACCORD_ICONS, ACCORD_LABELS } from '@/app/perfume-network/config';

interface NoteAnalysisProps {
  topNotes: string[];
  middleNotes: string[];
  baseNotes: string[];
}

/**
 * 향수 맵(NMap) 노드 분석 컴포넌트
 * Top, Middle, Base 노드의 구성을 시각적으로 보여줍니다.
 */
const NoteAnalysis = ({ topNotes, middleNotes, baseNotes }: NoteAnalysisProps) => {
  const noteGroups = [
    { title: 'Top Notes', notes: topNotes, description: '첫 인상을 결정하는 향기', color: '#F6B3C6' },
    { title: 'Middle Notes', notes: middleNotes, description: '향기의 중심이 되는 테마', color: '#5FBED7' },
    { title: 'Base Notes', notes: baseNotes, description: '오랫동안 남는 잔향의 깊이', color: '#6B4F2A' },
  ];

  const getAccordLabel = (acc: string) => ACCORD_LABELS[acc] || acc;
  const getAccordIcon = (acc: string) => ACCORD_ICONS[acc] || Sparkles;
  const getAccordColor = (acc: string) => ACCORD_COLORS[acc] || '#E6DDCF';

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-[#1F1F1F]">향기 노트 분석</h2>
        <p className="text-sm text-[#7A6B57]">당신이 탐색한 향기들의 계층별 구성을 분석했습니다.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {noteGroups.map((group) => (
          <div 
            key={group.title} 
            className="bg-white rounded-2xl p-6 border border-[#E6DDCF] shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-2 mb-4">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: group.color }}
              />
              <h3 className="font-bold text-[#4D463A]">{group.title}</h3>
            </div>
            
            <p className="text-[11px] text-[#9C8D7A] mb-4">{group.description}</p>
            
            <div className="space-y-3">
              {group.notes.length > 0 ? (
                group.notes.map((note) => {
                  const Icon = getAccordIcon(note);
                  return (
                    <div key={note} className="flex items-center justify-between group">
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-[#7A6B57]" strokeWidth={1.75} />
                        <span className="text-sm font-medium text-[#5C5448] group-hover:text-[#C8A24D] transition-colors">
                          {getAccordLabel(note)}
                        </span>
                      </div>
                      <div 
                        className="w-1.5 h-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ backgroundColor: getAccordColor(note) }}
                      />
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-[#E2D7C5] italic py-2">분석된 노트가 없습니다.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default NoteAnalysis;
