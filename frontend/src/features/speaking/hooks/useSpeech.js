import { useState, useEffect, useCallback } from 'react';

export function useSpeech() {
  const [voices, setVoices] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    const loadVoices = () => {
      setVoices(window.speechSynthesis.getVoices());
    };
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
    
    return () => {
      window.speechSynthesis.cancel();
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  const getVoiceForPreset = useCallback((preset) => {
    if (!voices.length) return null;
    
    let targetLang = 'en-US';
    let genderHint = 'female';
    
    if (preset === 'US-Female') { targetLang = 'en-US'; genderHint = 'female'; }
    if (preset === 'UK-Male') { targetLang = 'en-GB'; genderHint = 'male'; }
    if (preset === 'AU-Female') { targetLang = 'en-AU'; genderHint = 'female'; }

    const langVoices = voices.filter(v => v.lang.startsWith(targetLang) || v.lang.startsWith(targetLang.replace('-', '_')));
    const fallbackEN = voices.find(v => v.lang.startsWith('en')) || voices[0];
    
    if (langVoices.length === 0) return fallbackEN;

    const matchesGender = langVoices.filter(v => v.name.toLowerCase().includes(genderHint) || (genderHint === 'female' && v.name.includes('Samantha')));
    if (matchesGender.length > 0) return matchesGender[0];
    
    return langVoices[0] || fallbackEN;
  }, [voices]);

  const preview = useCallback((text, preset, rate) => {
    window.speechSynthesis.cancel();
    if (!text) return;
    
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = getVoiceForPreset(preset);
    if (voice) utterance.voice = voice;
    utterance.rate = rate || 1.0;
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    window.speechSynthesis.speak(utterance);
  }, [getVoiceForPreset]);

  const speak = useCallback((text) => {
    window.speechSynthesis.cancel();
    if (!text) return;
    
    const pref = JSON.parse(localStorage.getItem('speaking_voice') || 'null');
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (pref && pref.preset) {
      const voice = getVoiceForPreset(pref.preset);
      if (voice) utterance.voice = voice;
      utterance.rate = pref.rate || 1.0;
    } else {
      const voice = voices.find(v => v.lang.startsWith('en')) || voices[0];
      if (voice) utterance.voice = voice;
    }
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    window.speechSynthesis.speak(utterance);
  }, [voices, getVoiceForPreset]);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  return { voicesLoaded: voices.length > 0, isSpeaking, speak, stop, preview };
}
