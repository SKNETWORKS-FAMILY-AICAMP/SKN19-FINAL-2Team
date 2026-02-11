import { useState, useCallback } from 'react';
import Cropper from 'react-easy-crop';
import getCroppedImg from '@/lib/cropImage';

interface Props {
    imageSrc: string;
    onClose: () => void;
    onCropComplete: (croppedBlob: Blob) => void;
}

export default function ImageCropperModal({ imageSrc, onClose, onCropComplete }: Props) {
    const [crop, setCrop] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [croppedAreaPixels, setCroppedAreaPixels] = useState<any>(null);

    const onCropChange = (crop: { x: number; y: number }) => setCrop(crop);
    const onZoomChange = (zoom: number) => setZoom(zoom);

    const onCropCompleteHandler = useCallback((_: any, croppedAreaPixels: any) => {
        setCroppedAreaPixels(croppedAreaPixels);
    }, []);

    const handleSave = async () => {
        try {
            const croppedImage = await getCroppedImg(imageSrc, croppedAreaPixels);
            if (croppedImage) {
                onCropComplete(croppedImage);
            }
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="bg-white p-6 rounded-2xl w-[90%] max-w-md shadow-2xl relative animate-in fade-in zoom-in duration-300">
                <h3 className="text-lg font-bold mb-4 text-center">프로필 이미지 편집</h3>

                {/* 크롭 영역 (높이 고정) */}
                <div className="relative w-full h-[300px] bg-[#333] rounded-xl overflow-hidden mb-6">
                    <Cropper
                        image={imageSrc}
                        crop={crop}
                        zoom={zoom}
                        aspect={1}
                        cropShape="round"
                        showGrid={false}
                        onCropChange={onCropChange}
                        onZoomChange={onZoomChange}
                        onCropComplete={onCropCompleteHandler}
                    />
                </div>

                {/* 줌 슬라이더 */}
                <div className="mb-6 px-2">
                    <div className="flex justify-between text-xs text-gray-500 mb-2">
                        <span>축소</span>
                        <span>확대</span>
                    </div>
                    <input
                        type="range"
                        value={zoom}
                        min={1}
                        max={3}
                        step={0.1}
                        aria-labelledby="Zoom"
                        onChange={(e) => setZoom(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black"
                    />
                </div>

                {/* 버튼 */}
                <div className="flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 py-3 rounded-xl font-bold bg-gray-100 text-gray-600 hover:bg-gray-200 transition"
                    >
                        취소
                    </button>
                    <button
                        onClick={handleSave}
                        className="flex-1 py-3 rounded-xl font-bold bg-black text-white hover:bg-gray-800 transition shadow-lg"
                    >
                        저장하기
                    </button>
                </div>
            </div>
        </div>
    );
}
