/* CabinetShelf.tsx (Refined Frame & Triangle) */
"use client";

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    name_en?: string;
    name_kr?: string;
    brand: string;
    brand_kr?: string; // 추가
    image_url: string | null;
    status: string;
}

interface Props {
    perfume: MyPerfume;
    onSelect: (perfume: MyPerfume) => void;
    isKorean: boolean; // prop 추가
}

export default function CabinetShelf({ perfume, onSelect, isKorean }: Props) {
    // 상태별 색상 (삼각형)
    const cornerColor = perfume.status === 'HAVE' ? 'border-t-indigo-600' :
        perfume.status === 'HAD' ? 'border-t-amber-500' :
            (perfume.status === 'WANT' || perfume.status === 'RECOMMENDED') ? 'border-t-rose-500' : 'border-t-gray-400';

    return (
        <div
            onClick={() => onSelect(perfume)}
            className="
        bg-white rounded-xl md:rounded-2xl relative group cursor-pointer
        border border-gray-100 hover:border-[#C5A55D]/50
        shadow-sm hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1
        flex flex-col h-full overflow-hidden p-1.5 md:p-3
      "
        >
            {/* 
        이미지 컨테이너 (Inner Box) 
        - 패딩을 줄여서 프레임 느낌 축소
        - 사진 모서리에 삼각형 배치
      */}
            <div className="w-full aspect-square relative bg-gray-50 rounded-lg overflow-hidden group-hover:bg-[#FFFCF5] transition-colors duration-500">

                {/* 모서리 삼각형 (Image Corner) */}
                <div
                    className={`
            absolute top-0 left-0 z-20 w-0 h-0 
            border-t-[20px] md:border-t-[28px] border-r-[20px] md:border-r-[28px] 
            border-r-transparent ${cornerColor}
            drop-shadow-sm opacity-90
          `}
                />

                {/* 이미지 (꽉 차게) */}
                <div className="absolute inset-0 p-1.5 md:p-3 flex items-center justify-center">
                    {perfume.image_url ? (
                        <img
                            src={perfume.image_url}
                            alt={perfume.name}
                            className="w-full h-full object-contain drop-shadow-md group-hover:scale-105 transition duration-500 will-change-transform mix-blend-multiply"
                        />
                    ) : (
                        <div className="text-gray-300 text-[8px] md:text-xs">No Image</div>
                    )}
                </div>
            </div>

            {/* Text Info */}
            <div className="mt-1 md:mt-2 text-center px-0.5 md:px-1">
                {(() => {
                    const brand = isKorean && perfume.brand_kr ? perfume.brand_kr : perfume.brand;
                    const isBrandLong = brand.length > 6;
                    return (
                        <p className={`
                            tracking-widest text-gray-400 uppercase font-medium break-keep leading-[1.1]
                            ${isBrandLong
                                ? 'text-[7px] md:text-[8px] line-clamp-2'
                                : 'text-[8px] md:text-[9px] line-clamp-1'}
                        `}>
                            {brand}
                        </p>
                    );
                })()}
                {(() => {
                    const name = isKorean && perfume.name_kr ? perfume.name_kr : (perfume.name_en || perfume.name);
                    const isLong = name.length >= 8;

                    return (
                        <h3 className={`
                            font-bold text-gray-900 mt-0.5 md:mt-1 leading-[1.1] transition-colors group-hover:text-[#C5A55D] break-keep
                            ${isLong
                                ? 'text-[9px] md:text-sm line-clamp-2'
                                : 'text-[10px] md:text-sm line-clamp-1'}
                        `}>
                            {name}
                        </h3>
                    );
                })()}
            </div>
        </div>
    );
}
