import { pageImageUrl } from "../api";

interface Props {
  manualId: string;
  page: number;
  onClose: () => void;
}

export default function PageImageModal({ manualId, page, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-full max-w-3xl overflow-auto rounded-lg bg-neutral-900 p-3 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between text-sm text-neutral-300">
          <span>Page {page}</span>
          <button
            onClick={onClose}
            className="rounded px-2 py-1 text-neutral-400 hover:bg-neutral-800 hover:text-white"
          >
            Close
          </button>
        </div>
        <img
          src={pageImageUrl(manualId, page)}
          alt={`Manual page ${page}`}
          className="max-w-full rounded"
        />
      </div>
    </div>
  );
}
