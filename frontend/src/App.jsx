import React, { useState } from 'react';
import axios from 'axios';
import AudioRecorder from './components/AudioRecorder';
import { Activity, Copy, CheckCircle, AlertCircle, Mic, Type, ArrowRight, Loader2 } from 'lucide-react';

function App() {
  const [workoutData, setWorkoutData] = useState(null);
  const [inputMode, setInputMode] = useState('voice'); // 'voice' or 'text'
  const [textInput, setTextInput] = useState('');
  const [isProcessingText, setIsProcessingText] = useState(false);

  const handleAnalysisComplete = (data) => {
    setWorkoutData(data);
  };

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!textInput.trim()) return;

    setIsProcessingText(true);
    setWorkoutData(null);

    try {
      const parseResponse = await axios.post('http://localhost:8000/parse', { text: textInput });
      setWorkoutData(parseResponse.data);
    } catch (error) {
      console.error("Error processing text:", error);
      setWorkoutData({ error: "Could not process text. Ensure backend is running." });
    } finally {
      setIsProcessingText(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-1.5 rounded-lg">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Coach AI Assistant</h1>
          </div>
          <div className="text-sm font-medium text-slate-500">MVP (Data Collection Mode)</div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10 text-center space-y-3">
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Workout Assignment</h2>
          <p className="text-slate-600 max-w-xl mx-auto">
            Assign workouts using voice commands or text instructions.
          </p>
        </div>

        {/* Input Mode Switcher */}
        <div className="flex justify-center mb-8">
          <div className="bg-slate-100 p-1 rounded-lg inline-flex relative">
            {/* Sliding Background */}
            <div
              className={`absolute inset-y-1 w-1/2 bg-white rounded-md shadow-sm transition-all duration-200 ${inputMode === 'voice' ? 'left-1' : 'left-1/2 ml-[-4px] translate-x-1'
                }`}
              style={{ width: 'calc(50% - 4px)' }}
            ></div>

            <button
              onClick={() => setInputMode('voice')}
              className={`relative z-10 px-6 py-2 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${inputMode === 'voice' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                }`}
            >
              <Mic className="w-4 h-4" />
              Voice
            </button>
            <button
              onClick={() => setInputMode('text')}
              className={`relative z-10 px-6 py-2 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${inputMode === 'text' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                }`}
            >
              <Type className="w-4 h-4" />
              Text
            </button>
          </div>
        </div>

        {/* Input Areas */}
        <div className="max-w-md mx-auto min-h-[200px]">
          {inputMode === 'voice' ? (
            <AudioRecorder onAnalysisComplete={handleAnalysisComplete} />
          ) : (
            <form onSubmit={handleTextSubmit} className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Enter Workout Instructions
              </label>
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="e.g., Assign a 10km run to Sarah at 7am"
                className="w-full h-32 p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none text-slate-800 placeholder:text-slate-400"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleTextSubmit(e);
                  }
                }}
              />
              <button
                type="submit"
                disabled={!textInput.trim() || isProcessingText}
                className="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {isProcessingText ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    Process Instruction
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
              <p className="mt-2 text-xs text-slate-400 text-center">Press Enter to submit</p>
            </form>
          )}
        </div>

        {/* Error State */}
        {workoutData && workoutData.error && (
          <div className="mt-8 mx-auto max-w-md bg-red-50 border border-red-100 p-4 rounded-lg flex items-center gap-3 text-red-700 animate-in fade-in slide-in-from-top-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm font-medium">{workoutData.error} Please try again.</p>
          </div>
        )}

        {/* Success State - Dynamic Table View */}
        {workoutData && !workoutData.error && workoutData.assignments && workoutData.assignments.length > 0 && (
          <div className="mt-12 animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
            {workoutData.assignments.map((assignment, idx) => (
              <div key={idx} className="bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
                <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                  <h3 className="font-semibold text-slate-800">
                    {workoutData.assignments.length > 1
                      ? `Assignment ${idx + 1}`
                      : 'Parsed Assignment'}
                  </h3>
                  <span className={`text-xs px-2 py-1 rounded-full border ${workoutData.confidence === 'High' ? 'bg-green-50 border-green-200 text-green-700' :
                    workoutData.confidence === 'Medium' ? 'bg-yellow-50 border-yellow-200 text-yellow-700' :
                      'bg-slate-100 border-slate-200 text-slate-600'
                    }`}>
                    {workoutData.confidence} Confidence
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50/50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-100">
                      <tr>
                        <th className="px-6 py-3 w-1/3">Attribute</th>
                        <th className="px-6 py-3">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {assignment.attributes.map((attr, attrIdx) => (
                        <tr key={attrIdx} className="hover:bg-slate-50/50 transition-colors">
                          <td className="px-6 py-3 font-medium text-slate-700">{attr.key}</td>
                          <td className="px-6 py-3 text-slate-900">
                            {attr.key === 'Activity' ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                                {attr.value}
                              </span>
                            ) : attr.key === 'Intensity' ? (
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${attr.value === 'Easy' ? 'bg-green-100 text-green-800' :
                                  attr.value === 'Moderate' ? 'bg-yellow-100 text-yellow-800' :
                                    attr.value === 'Hard' ? 'bg-red-100 text-red-800' :
                                      'bg-slate-100 text-slate-800'
                                }`}>
                                {attr.value}
                              </span>
                            ) : (
                              attr.value
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}

            <div className="mt-6">
              <details className="group">
                <summary className="list-none flex items-center cursor-pointer text-sm text-slate-500 hover:text-indigo-600 transition-colors">
                  <span className="mr-2 group-open:rotate-90 transition-transform">▸</span>
                  View Engineer/Debug Data (JSON)
                </summary>
                <div className="mt-2 bg-slate-900 rounded-lg p-4 relative group/code">
                  <button
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(workoutData, null, 2))}
                    className="absolute top-3 right-3 text-white/50 hover:text-white transition-colors"
                    title="Copy JSON"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <pre className="text-slate-300 font-mono text-xs overflow-auto max-h-60">
                    {JSON.stringify(workoutData, null, 2)}
                  </pre>
                </div>
              </details>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <button
                onClick={() => setWorkoutData(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
              >
                Discard
              </button>
              <button className="px-6 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm hover:shadow transition-all flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Confirm Assignment
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
