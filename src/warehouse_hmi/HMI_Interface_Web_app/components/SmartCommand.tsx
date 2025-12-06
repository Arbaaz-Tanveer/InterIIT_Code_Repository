import React, { useState, useEffect, useRef } from 'react';
import { GoogleGenAI } from '@google/genai';
import { Mic, Send, Sparkles, Loader2, Volume2, VolumeX } from 'lucide-react';
import { robotService } from '../services/robotService';
import { RACKS } from '../constants';

// Speech Recognition Types
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: Event) => void;
  onend: (event: Event) => void;
}

declare global {
  interface Window {
    SpeechRecognition: { new(): SpeechRecognition };
    webkitSpeechRecognition: { new(): SpeechRecognition };
  }
}

export const SmartCommand: React.FC = () => {
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        handleCommand(transcript); // Auto-submit
      };

      recognitionRef.current.onerror = (event: Event) => {
        console.error('Speech recognition error', event);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const speakResponse = (text: string) => {
    if ('speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    }
  };

  const handleCommand = async (manualInput?: string) => {
    const commandText = manualInput || input;
    if (!commandText.trim() || !import.meta.env.VITE_API_KEY) {
      if (!import.meta.env.VITE_API_KEY) {
        setAiResponse("Error: API Key not configured. Please create a .env file with VITE_API_KEY=your_key");
      }
      return;
    }

    setIsThinking(true);
    setAiResponse(null);

    try {
      const ai = new GoogleGenAI({ apiKey: import.meta.env.VITE_API_KEY });

      // Build rack information
      const rackInfo = RACKS.map(r => `${r.label}: position (${r.position.x}, ${r.position.y})`).join(', ');

      // Context about the environment to help Gemini understand
      const context = `You are controlling a warehouse robot via natural language commands.

Available racks: Rack 1, Rack 2, Rack 3, Rack 4, Rack 5.

Available commands:
- SCAN: Scan specific racks. Requires a list of rack numbers (e.g., [1, 2, 3]).
- STOP: Stop the robot immediately.
- RESTART: Restart the robot or return to base.
- START_AUTO_SCAN: Start the automatic scanning sequence.
- STOP_AUTO_SCAN: Stop the automatic scanning sequence.
- CLARIFY: Ask the user for more details if the command is ambiguous.
- CHAT: General conversation or questions not related to robot control.

Your task:
1. Parse the user's natural language command. You MUST understand **Hindi** and **English**.
2. Map "Go to rack X" or "Check rack X" to the SCAN command.
3. If the user speaks Hindi, translate the intent to the appropriate command (e.g., "Auto scan roko" -> STOP_AUTO_SCAN).
4. If the input is a general question (e.g., "How are you?", "What is the capital of India?"), use the CHAT action.
5. Return a JSON response in this EXACT format:
{
  "action": "STOP" | "SCAN" | "RESTART" | "START_AUTO_SCAN" | "STOP_AUTO_SCAN" | "CLARIFY" | "CHAT",
  "target": "rack label or description",
  "racks": number[] (array of rack numbers, for SCAN),
  "message": "A brief confirmation message, clarification question, or chat response. If user speaks Hindi, reply in Hindi."
}

Examples:
User: "Go to rack 1" or "Check rack 1"
Response: {"action":"SCAN","target":"Rack 1","racks":[1],"message":"Heading to scan Rack 1"}

User: "Rack 1 aur 3 ko check karo" (Hindi for "Check rack 1 and 3")
Response: {"action":"SCAN","target":"Rack 1, 3","racks":[1, 3],"message":"Rack 1 aur 3 scan karne ja raha hoon"}

User: "Stop the robot" or "Ruk jao"
Response: {"action":"STOP_AUTO_SCAN","target":"System","message":"Stopping auto scan"}

User: "Start auto scan" or "Auto scan shuru karo"
Response: {"action":"START_AUTO_SCAN","target":"System","message":"Auto scan shuru kar raha hoon"}

User: "Restart"
Response: {"action":"RESTART","target":"System","message":"Restarting robot system"}

User: "Go to the rack" (Ambiguous)
Response: {"action":"CLARIFY","target":"User","message":"Kaunse rack pe jana hai?"}

User: "Hello" or "Kaise ho?"
Response: {"action":"CHAT","target":"User","message":"Main theek hoon! Main aapki kya madad kar sakta hoon?"}

IMPORTANT: Return ONLY valid JSON. Do not include markdown formatting like \`\`\`json. Just the raw JSON object.`;

      const response = await ai.models.generateContent({
        model: 'gemini-2.0-flash-exp',
        contents: `${context}\n\nUser Command: "${commandText}"`,
      });

      const text = response.text.trim();
      console.log("AI Raw Response:", text); // Debugging

      let parsedCommand;

      // Try to extract JSON from the response
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          parsedCommand = JSON.parse(jsonMatch[0]);
        } catch (e) {
          console.warn("JSON parse failed, falling back to chat", e);
        }
      }

      // Fallback: If no JSON or parse failed, treat as CHAT
      if (!parsedCommand) {
        parsedCommand = {
          action: 'CHAT',
          target: 'User',
          message: text // Use the raw text as the message
        };
      }

      // Display AI response
      const message = parsedCommand.message || 'Command processed';
      setAiResponse(message);
      speakResponse(message);

      // Execute the command
      if (parsedCommand.action === 'STOP') {
        await robotService.sendCommand('STOP');
      } else if (parsedCommand.action === 'START_AUTO_SCAN') {
        await robotService.sendCommand('START_AUTO_SCAN');
      } else if (parsedCommand.action === 'STOP_AUTO_SCAN') {
        await robotService.sendCommand('STOP_AUTO_SCAN');
      } else if (parsedCommand.action === 'SCAN' && parsedCommand.racks) {
        robotService.sendScanRackCommand(parsedCommand.racks);
      } else if (parsedCommand.action === 'RESTART') {
        robotService.sendRestartCommand();
      } else if (parsedCommand.action === 'CLARIFY' || parsedCommand.action === 'CHAT') {
        // Just speaking the message
      }

    } catch (error) {
      console.error("AI Error", error);
      const errorMessage = "Error: Could not understand command. Please try again.";
      setAiResponse(errorMessage);
      speakResponse("I'm sorry, I couldn't understand that command.");

      // Fallback: Try simple keyword matching
      const lower = commandText.toLowerCase();
      if (lower.includes('stop') || lower.includes('halt')) {
        robotService.sendCommand('STOP');
        const msg = "Stopping robot";
        setAiResponse(msg);
        speakResponse(msg);
      } else if (lower.includes('scan')) {
        // Simple regex to find numbers
        const numbers = lower.match(/\d+/g)?.map(Number);
        if (numbers && numbers.length > 0) {
          robotService.sendScanRackCommand(numbers);
          const msg = `Scanning racks: ${numbers.join(', ')}`;
          setAiResponse(msg);
          speakResponse(msg);
        }
      } else if (lower.includes('restart') || lower.includes('return') || lower.includes('base')) {
        robotService.sendRestartCommand();
        const msg = "Restarting robot system";
        setAiResponse(msg);
        speakResponse(msg);
      } else {
        // Try to find rack mention
        const rack = RACKS.find(r =>
          lower.includes(r.label.toLowerCase()) ||
          lower.includes(r.id.toLowerCase())
        );
        if (rack) {
          robotService.sendCommand('GOTO', { x: rack.position.x, y: rack.position.y });
          const msg = `Moving to ${rack.label}`;
          setAiResponse(msg);
          speakResponse(msg);
        }
      }
    } finally {
      setIsThinking(false);
      setInput('');
    }
  };

  return (
    <div className="bg-sci-panel border border-slate-700 rounded-xl p-4 shadow-lg">
      <div className="flex items-center space-x-2 mb-3 text-sci-accent">
        <Sparkles size={18} />
        <h3 className="font-semibold">AI Commander</h3>
      </div>

      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCommand()}
          placeholder={isListening ? "Listening..." : "e.g., 'Go to Rack A1' or 'Return to charging dock'"}
          className={`w-full bg-slate-900 border ${isListening ? 'border-sci-accent animate-pulse' : 'border-slate-700'} rounded-lg pl-12 pr-12 py-3 text-sm focus:outline-none focus:border-sci-accent transition-colors`}
        />

        {/* Mic Button */}
        <button
          onClick={toggleListening}
          className={`absolute left-2 top-1/2 -translate-y-1/2 p-1.5 rounded transition-colors ${isListening
            ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
            : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          title={isListening ? "Stop Listening" : "Start Voice Command"}
        >
          <Mic size={18} className={isListening ? "animate-pulse" : ""} />
        </button>

        {/* Send Button */}
        <button
          onClick={() => handleCommand()}
          disabled={isThinking}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-sci-accent/10 text-sci-accent rounded hover:bg-sci-accent hover:text-white transition-colors disabled:opacity-50"
        >
          {isThinking ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
        </button>
      </div>

      {aiResponse && (
        <div className="mt-3 p-3 bg-slate-800/50 border border-slate-700 rounded text-sm text-slate-300 font-mono animate-in fade-in slide-in-from-top-2 flex justify-between items-start">
          <div>
            <span className="text-sci-success font-bold">{'> '}</span>
            {aiResponse}
          </div>
          {isSpeaking && (
            <Volume2 size={16} className="text-sci-accent animate-pulse ml-2 flex-shrink-0" />
          )}
        </div>
      )}
    </div>
  );
};
