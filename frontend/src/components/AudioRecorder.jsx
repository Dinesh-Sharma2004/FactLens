import { useRef, useState } from "react";

export default function AudioRecorder({ onAudioReady }) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const stopRecorderTracks = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stopRecorderTracks();
        if (onAudioReady) {
          await onAudioReady(blob);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      stopRecorderTracks();
      setIsRecording(false);
      console.error("Microphone access failed:", error);
    }
  };

  return (
    <button
      onClick={toggleRecording}
      className={`
        group relative flex items-center justify-center w-10 h-10 rounded-xl transition-all
        ${isRecording ? "bg-brand text-white animate-pulse" : "bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-brand/10 hover:text-brand"}
      `}
      title={isRecording ? "Stop Recording" : "Record Voice"}
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 013-3h0a3 3 0 013 3v8a3 3 0 01-3 3z" />
      </svg>
    </button>
  );
}
