import React, { useRef, useState, useEffect } from 'react';
import { X, Check, Pen, Circle as CircleIcon, MoveUpRight, Undo } from 'lucide-react';

interface ImageAnnotationModalProps {
    isOpen: boolean;
    imageFile: File | null;
    onClose: () => void;
    onSave: (annotatedSnippet: Blob) => void;
}

type ToolType = 'pen' | 'arrow' | 'circle';

export const ImageAnnotationModal: React.FC<ImageAnnotationModalProps> = ({ isOpen, imageFile, onClose, onSave }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [imageObj, setImageObj] = useState<HTMLImageElement | null>(null);
    const [activeTool, setActiveTool] = useState<ToolType>('arrow');
    const [color, setColor] = useState('#ef4444'); // Red default
    const [isDrawing, setIsDrawing] = useState(false);
    const [startPos, setStartPos] = useState<{ x: number, y: number } | null>(null);

    // History for undo (simple stack of image data URLs)
    const [history, setHistory] = useState<string[]>([]);

    useEffect(() => {
        if (imageFile) {
            const img = new Image();
            img.src = URL.createObjectURL(imageFile);
            img.onload = () => {
                setImageObj(img);
                setHistory([]); // reset history
            };
        } else {
            setImageObj(null);
            setHistory([]);
        }
    }, [imageFile]);

    useEffect(() => {
        if (isOpen && imageObj && canvasRef.current) {
            const canvas = canvasRef.current;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            // Fit canvas to screen while maintaining aspect ratio, or max reasonable size
            // For simplicity, we limit max height/width to 800px or window size
            const maxWidth = Math.min(window.innerWidth - 40, 800);
            const maxHeight = Math.min(window.innerHeight - 200, 600);

            let w = imageObj.width;
            let h = imageObj.height;

            const ratio = Math.min(maxWidth / w, maxHeight / h);

            canvas.width = w * ratio;
            canvas.height = h * ratio;

            // Draw initial image
            ctx.drawImage(imageObj, 0, 0, canvas.width, canvas.height);
            saveToHistory();
        }
    }, [isOpen, imageObj]); // Re-run when opened or image loaded

    const saveToHistory = () => {
        const canvas = canvasRef.current;
        if (canvas) {
            setHistory(prev => [...prev.slice(-9), canvas.toDataURL()]);
        }
    };

    const restoreFromHistory = () => {
        if (history.length <= 1) return; // Keep at least original

        const newHistory = [...history];
        newHistory.pop(); // Remove current state
        const prevState = newHistory[newHistory.length - 1];
        setHistory(newHistory);

        const img = new Image();
        img.src = prevState;
        img.onload = () => {
            const canvas = canvasRef.current;
            const ctx = canvas?.getContext('2d');
            if (canvas && ctx) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
            }
        }
    };

    const getMousePos = (e: React.MouseEvent | React.TouchEvent) => {
        const canvas = canvasRef.current;
        if (!canvas) return { x: 0, y: 0 };
        const rect = canvas.getBoundingClientRect();

        let clientX, clientY;
        if ('touches' in e) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        } else {
            clientX = (e as React.MouseEvent).clientX;
            clientY = (e as React.MouseEvent).clientY;
        }

        return {
            x: clientX - rect.left,
            y: clientY - rect.top
        };
    };

    const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
        e.preventDefault(); // Prevent scrolling on touch
        setIsDrawing(true);
        const pos = getMousePos(e);
        setStartPos(pos);

        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (ctx) {
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
            ctx.strokeStyle = color;
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        }
    };

    const draw = (e: React.MouseEvent | React.TouchEvent) => {
        if (!isDrawing || !startPos) return;
        e.preventDefault();
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (!canvas || !ctx) return;

        const currentPos = getMousePos(e);

        if (activeTool === 'pen') {
            ctx.lineTo(currentPos.x, currentPos.y);
            ctx.stroke();
        } else {
            // For shapes, we need to clear and redraw simply (using a temp buffer or just restoring last history state)
            // Efficient way: Restore last history image then draw shape on top
            const lastState = history[history.length - 1];
            const img = new Image();
            img.src = lastState;
            // Draw synchronously if cached (it should be for DataURL), but onload is safer
            // For responsiveness in this simple app, we can cheat a bit or use a second canvas layer.
            // Let's try simple clear and redraw from history for now.
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);

            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 4;

            if (activeTool === 'circle') {
                const radius = Math.sqrt(Math.pow(currentPos.x - startPos.x, 2) + Math.pow(currentPos.y - startPos.y, 2));
                ctx.arc(startPos.x, startPos.y, radius, 0, 2 * Math.PI);
                ctx.stroke();
            } else if (activeTool === 'arrow') {
                drawArrow(ctx, startPos.x, startPos.y, currentPos.x, currentPos.y);
            }
        }
    };

    const drawArrow = (ctx: CanvasRenderingContext2D, fromX: number, fromY: number, toX: number, toY: number) => {
        const headlen = 15; // length of head in pixels
        const dx = toX - fromX;
        const dy = toY - fromY;
        const angle = Math.atan2(dy, dx);
        ctx.moveTo(fromX, fromY);
        ctx.lineTo(toX, toY);
        ctx.lineTo(toX - headlen * Math.cos(angle - Math.PI / 6), toY - headlen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headlen * Math.cos(angle + Math.PI / 6), toY - headlen * Math.sin(angle + Math.PI / 6));
        ctx.stroke();
    };

    const stopDrawing = () => {
        if (isDrawing) {
            setIsDrawing(false);
            setStartPos(null);
            saveToHistory();
        }
    };

    const handleSave = () => {
        const canvas = canvasRef.current;
        if (canvas) {
            // Convert to blob
            canvas.toBlob((blob) => {
                if (blob) {
                    onSave(blob);
                    onClose();
                }
            }, 'image/jpeg', 0.85); // JPEG compression
        }
    };

    if (!isOpen || !imageFile) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center p-4">
            {/* Header / Tools */}
            <div className="w-full max-w-4xl flex justify-between items-center mb-4 text-white">
                <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition">
                    <X className="w-6 h-6" />
                </button>

                <div className="flex bg-white/10 rounded-full p-2 space-x-2 backdrop-blur-sm">
                    <button
                        onClick={() => setActiveTool('pen')}
                        className={`p-2 rounded-full transition ${activeTool === 'pen' ? 'bg-white text-black' : 'hover:bg-white/20'}`}
                    >
                        <Pen className="w-5 h-5" />
                    </button>
                    <button
                        onClick={() => setActiveTool('arrow')}
                        className={`p-2 rounded-full transition ${activeTool === 'arrow' ? 'bg-white text-black' : 'hover:bg-white/20'}`}
                    >
                        <MoveUpRight className="w-5 h-5" />
                    </button>
                    <button
                        onClick={() => setActiveTool('circle')}
                        className={`p-2 rounded-full transition ${activeTool === 'circle' ? 'bg-white text-black' : 'hover:bg-white/20'}`}
                    >
                        <CircleIcon className="w-5 h-5" />
                    </button>
                    <div className="w-px bg-white/20 mx-2" />
                    <button
                        onClick={() => setColor(color === '#ef4444' ? '#3b82f6' : '#ef4444')} // Simple toggle red/blue for now
                        className="w-9 h-9 rounded-full border-2 border-white"
                        style={{ backgroundColor: color }}
                    />
                </div>

                <div className="flex space-x-2">
                    <button onClick={restoreFromHistory} disabled={history.length <= 1} className="p-2 hover:bg-white/10 rounded-full transition disabled:opacity-30">
                        <Undo className="w-6 h-6" />
                    </button>
                    <button onClick={handleSave} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-full font-medium flex items-center space-x-2">
                        <Check className="w-4 h-4" />
                        <span>Fertig</span>
                    </button>
                </div>
            </div>

            {/* Canvas Area */}
            <div className="relative overflow-hidden rounded-lg shadow-2xl bg-black">
                <canvas
                    ref={canvasRef}
                    onMouseDown={startDrawing}
                    onMouseMove={draw}
                    onMouseUp={stopDrawing}
                    onMouseLeave={stopDrawing}
                    onTouchStart={startDrawing}
                    onTouchMove={draw}
                    onTouchEnd={stopDrawing}
                    className="cursor-crosshair touch-none"
                />
            </div>
            <p className="text-white/50 text-sm mt-4">
                Zeichnen Sie auf das Bild, um Details hervorzuheben.
            </p>
        </div>
    );
};
