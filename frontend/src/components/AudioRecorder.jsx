import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Mic, Square, Loader2, Play } from 'lucide-react';

const AudioRecorder = ({ onAnalysisComplete }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [audioURL, setAudioURL] = useState(null);
    const [transcript, setTranscript] = useState('');
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = handleStop;
            mediaRecorderRef.current.start();
            setIsRecording(true);
            setAudioURL(null);
            setTranscript('');
        } catch (error) {
            console.error("Error accessing microphone:", error);
            alert("Could not access microphone. Please enable permissions.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const handleStop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);

        setIsProcessing(true);

        // Create form data to send to backend
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');

        try {
            // 1. Transcribe
            const transcribeResponse = await axios.post('http://localhost:8000/transcribe', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const text = transcribeResponse.data.text;
            setTranscript(text);

            // 2. Parse
            const parseResponse = await axios.post('http://localhost:8000/parse', { text });
            onAnalysisComplete(parseResponse.data);

        } catch (error) {
            console.error("Error processing audio:", error);
            alert("Error processing audio. Ensure backend is running.");
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="flex flex-col items-center gap-6 p-6 bg-white rounded-xl shadow-md w-full max-w-md mx-auto border border-slate-100">
            <div className="text-center">
                <h2 className="text-xl font-semibold text-slate-800 mb-2">Voice Command</h2>
                <p className="text-slate-500 text-sm">Speak clearly to assign a workout.</p>
            </div>

            <div className="relative group">
                <div className={`absolute -inset-1 rounded-full blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200 ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-blue-500'}`}></div>
                <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isProcessing}
                    className={`relative w-20 h-20 flex items-center justify-center rounded-full transition-all duration-300 ${isRecording
                            ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/50'
                            : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-500/50'
                        } shadow-lg disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                    {isProcessing ? (
                        <Loader2 className="w-8 h-8 animate-spin" />
                    ) : isRecording ? (
                        <Square className="w-8 h-8 fill-current" />
                    ) : (
                        <Mic className="w-8 h-8" />
                    )}
                </button>
            </div>

            {isRecording && (
                <div className="flex items-center gap-2 text-red-500 font-medium animate-pulse text-sm">
                    <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                    Recording...
                </div>
            )}

            {transcript && (
                <div className="w-full text-left bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Transcript</p>
                    <p className="text-slate-700 italic">"{transcript}"</p>
                </div>
            )}

            {audioURL && (
                <audio src={audioURL} controls className="w-full h-8 mt-2" />
            )}
        </div>
    );
};

export default AudioRecorder;
