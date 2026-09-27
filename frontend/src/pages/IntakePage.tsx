// @ts-nocheck
import React, { useCallback, useState, useEffect, FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Mic, Send, Edit2, CheckCircle, ArrowRight, Loader2, MapPin, Search, AlertCircle, FileText } from "lucide-react";
import { spandanApi } from "../services/spandanApi";
import type { ClassificationResult, DraftView, IntakeResult, InputChannel } from "../types/api";

export default function IntakePage() {
  const navigate = useNavigate();
  const locState = useLocation().state as { text?: string; lang?: string } | null;
  
  const [language, setLanguage] = useState(locState?.lang || "en");
  const [text, setText] = useState(locState?.text || "");
  const [channel, setChannel] = useState<InputChannel>("text");
  
  // Phase 2: Intake state
  const [intakeResult, setIntakeResult] = useState<IntakeResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  
  // Phase 3: Classification state
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  
  // Phase 4: Drafting state
  const [draft, setDraft] = useState<DraftView | null>(null);
  const [isDrafting, setIsDrafting] = useState(false);
  
  // Phase 5: Filing state
  const [isFiling, setIsFiling] = useState(false);

  // If we came from the home page with text, auto-submit!
  useEffect(() => {
    if (locState?.text && !intakeResult && !isSubmitting) {
      submitIntake(locState.text, locState.lang || "en", "text");
    }
  }, [locState]);

  const submitIntake = async (rawText: string, lang: string, inputChannel: InputChannel) => {
    setIsSubmitting(true);
    try {
      const res = await spandanApi.submitTextIntake({ raw_text: rawText, language: lang, input_channel: inputChannel });
      setIntakeResult(res);
    } catch (e) {
      console.error(e);
      // Handle error gracefully
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirm = async () => {
    if (!intakeResult) return;
    setIsConfirming(true);
    try {
      const confirmed = await spandanApi.confirmIntake(intakeResult.complaint_id);
      setIntakeResult(confirmed);
      
      // Auto trigger classification
      const classRes = await spandanApi.runClassification(intakeResult.complaint_id);
      setClassification(classRes);
      
      // Auto trigger drafting
      setIsDrafting(true);
      const draftRes = await spandanApi.runDrafting(intakeResult.complaint_id);
      setDraft(draftRes);
    } catch (e) {
      console.error(e);
    } finally {
      setIsConfirming(false);
      setIsDrafting(false);
    }
  };

  const handleFile = async () => {
    if (!intakeResult) return;
    setIsFiling(true);
    try {
      await spandanApi.fileComplaint(intakeResult.complaint_id);
      navigate(`/complaints/${intakeResult.complaint_id}`);
    } catch (e) {
      console.error(e);
    } finally {
      setIsFiling(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim().length > 2) submitIntake(text, language, channel);
  };

  if (!intakeResult && !isSubmitting) {
    return (
      <div className="max-w-3xl mx-auto p-4 py-12">
        <h1 className="text-3xl font-bold mb-8 tracking-tight">Report a Complaint</h1>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
            <textarea 
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Tell us what happened..." 
              className="w-full resize-none outline-none text-lg p-4 h-32 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="flex items-center justify-between">
              <select 
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-white border border-slate-200 rounded-lg px-4 py-2 font-medium"
              >
                <option value="en">English</option>
                <option value="ta">Tamil</option>
                <option value="te">Telugu</option>
                <option value="hi">Hindi</option>
                <option value="ml">Malayalam</option>
                <option value="kn">Kannada</option>
              </select>
              <button 
                type="submit" 
                disabled={!text.trim()}
                className="flex items-center space-x-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                <span>Process Complaint</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // AI Pipeline View
  return (
    <div className="max-w-4xl mx-auto p-4 py-12">
      <h1 className="text-3xl font-bold mb-8 tracking-tight">Processing your complaint</h1>
      
      <div className="space-y-6">
        
        {/* Step 1: Intake & Understanding */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {isSubmitting ? <Loader2 className="animate-spin text-blue-600" /> : <CheckCircle className="text-emerald-600" />}
              <h2 className="text-lg font-semibold text-slate-900">Understanding Complaint</h2>
            </div>
          </div>
          
          {intakeResult && (
            <div className="p-6 bg-white">
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Issue Detected</div>
                  <div className="font-semibold text-slate-900 text-lg">{intakeResult.issue || "Not detected"}</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-500 mb-1">Location</div>
                  <div className="font-semibold text-slate-900 text-lg flex items-center">
                    <MapPin size={16} className="text-slate-400 mr-1" />
                    {intakeResult.location || "Not detected"}
                  </div>
                </div>
              </div>
              
              {!isConfirming && intakeResult.citizen_confirmation_status !== "CONFIRMED" && (
                <div className="flex space-x-4">
                  <button 
                    onClick={handleConfirm}
                    className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 flex items-center justify-center space-x-2 shadow-sm"
                  >
                    <CheckCircle size={18} />
                    <span>Yes, this is correct</span>
                  </button>
                  <button 
                    onClick={() => { setIntakeResult(null); setText(""); }}
                    className="flex-1 bg-white border border-slate-300 text-slate-700 py-3 rounded-xl font-medium hover:bg-slate-50 flex items-center justify-center space-x-2"
                  >
                    <Edit2 size={18} />
                    <span>Edit details</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Step 2: Classification */}
        {(isConfirming || classification) && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center space-x-3">
              {!classification ? <Loader2 className="animate-spin text-blue-600" /> : <CheckCircle className="text-emerald-600" />}
              <h2 className="text-lg font-semibold text-slate-900">Classifying & Routing</h2>
            </div>
            {classification && (
              <div className="p-6 flex flex-col md:flex-row md:items-center justify-between bg-emerald-50/30">
                <div>
                  <div className="text-sm font-medium text-emerald-800 mb-1">Assigned Department</div>
                  <div className="font-bold text-emerald-900 text-xl">{classification.category.department_id}</div>
                  <div className="text-sm text-emerald-700 mt-1">{classification.category.category_id}</div>
                </div>
                <div className="mt-4 md:mt-0 text-right">
                  <div className="text-sm font-medium text-slate-500 mb-1">Knowledge Source</div>
                  <div className="inline-flex items-center px-3 py-1 bg-white border border-slate-200 rounded-full text-xs font-medium text-slate-600">
                    <Search size={12} className="mr-1" />
                    Civic Rules DB
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Drafting & Filing */}
        {(isDrafting || draft) && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-bottom-4 delay-150">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center space-x-3">
              {!draft ? <Loader2 className="animate-spin text-blue-600" /> : <CheckCircle className="text-emerald-600" />}
              <h2 className="text-lg font-semibold text-slate-900">Formalizing Complaint</h2>
            </div>
            {draft && (
              <div className="p-6">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 mb-6">
                  <div className="flex items-center space-x-2 text-slate-700 font-medium mb-3 border-b border-slate-200 pb-3">
                    <FileText size={18} />
                    <span>Official English Translation</span>
                  </div>
                  <p className="text-slate-800 leading-relaxed font-serif">{draft.english_translation}</p>
                </div>
                
                <button 
                  onClick={handleFile}
                  disabled={isFiling}
                  className="w-full bg-slate-900 text-white py-4 rounded-xl font-bold hover:bg-slate-800 flex items-center justify-center space-x-2 shadow-md transition-transform active:scale-[0.99] disabled:opacity-70"
                >
                  {isFiling ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Filing with Mock Authority...</span>
                    </>
                  ) : (
                    <>
                      <span>File Official Complaint</span>
                      <ArrowRight size={20} />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
