import React, { useState, useEffect } from 'react';
import { Volume2, Square, Loader2 } from 'lucide-react';
import { useSpeech } from '../hooks/useSpeech.js';
import VoiceSetupModal from './VoiceSetupModal';

export default function SpeakButton({ text, className = "" }) {
  const { isSpeaking, speak, stop, voicesLoaded } = useSpeech();
  const [showModal, setShowModal] = useState(false);
  const [isPlayingThis, setIsPlayingThis] = useState(false);
  
  const handleClick = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    
    if (isSpeaking && isPlayingThis) {
      stop();
      setIsPlayingThis(false);
      return;
    }
    
    // If another is speaking, stop it first
    if (isSpeaking) {
      stop();
    }
    
    if (!text) return;
    
    const pref = localStorage.getItem('speaking_voice');
    if (!pref) {
      setShowModal(true);
    } else {
      doSpeak();
    }
  };

  const doSpeak = () => {
    setIsPlayingThis(true);
    speak(text);
  };

  useEffect(() => {
    if (!isSpeaking) setIsPlayingThis(false);
  }, [isSpeaking]);

  return (
    <>
      <button 
        onClick={handleClick}
        disabled={!text}
        className={`p-2 rounded-full border transition-all ${isSpeaking && isPlayingThis ? 'bg-red-50 text-red-500 border-red-200 hover:bg-red-100' : 'bg-white text-blue-600 border-gray-200 hover:bg-blue-50 hover:border-blue-300 disabled:opacity-50 disabled:cursor-not-allowed'} ${className}`}
        title={isSpeaking && isPlayingThis ? 'Dừng đọc' : 'Đọc văn bản'}
      >
        {!voicesLoaded && !isSpeaking ? (
          <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
        ) : isSpeaking && isPlayingThis ? (
          <Square className="w-4 h-4 fill-current" />
        ) : (
          <Volume2 className="w-4 h-4" />
        )}
      </button>

      {showModal && (
        <VoiceSetupModal 
          initialText={text}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false);
            // small delay to let modal close before reading
            setTimeout(doSpeak, 100);
          }}
        />
      )}
    </>
  );
}
