export default function ImageUpload({ onImageSelect }) {
  return (
    <label className="flex items-center justify-center w-10 h-10 bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-brand/10 hover:text-brand rounded-xl cursor-pointer transition-all" title="Upload Image">
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <input
        type="file"
        hidden
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && onImageSelect) {
            onImageSelect(file);
          }
          e.target.value = "";
        }}
      />
    </label>
  );
}
