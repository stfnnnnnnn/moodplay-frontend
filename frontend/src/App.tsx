import React, { useState } from 'react';
import logo from './assets/moodplay-logo.svg';
import { auth, googleProvider, db } from './firebase';
import { signInWithPopup } from 'firebase/auth';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';

export default function MoodPlayLanding() {
  const [isSignedIn, setIsSignedIn] = useState<boolean>(false);
  const [showTos, setShowTos] = useState<boolean>(false);
  const [isAuthenticating, setIsAuthenticating] = useState<boolean>(false);
  
  // States for ToS scroll logic
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState<boolean>(false);
  const [tosAccepted, setTosAccepted] = useState<boolean>(false);

  // Opens the Terms modal
  const initiateAuthFlow = () => {
    setHasScrolledToBottom(false);
    setTosAccepted(false);
    setShowTos(true);
  };

  // Checks if the user has scrolled to the bottom of the ToS text
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollTop + clientHeight >= scrollHeight - 5) {
      setHasScrolledToBottom(true);
    }
  };

  // Authentication function
  const handleGoogleSignIn = async () => {
    setShowTos(false); // Close modal before launching popup
    setIsAuthenticating(true);
    try {
      // 1. Google Login Popup
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      // 2. Hashing UID
      const encoder = new TextEncoder();
      const data = encoder.encode(user.uid + "moodplay_secret_salt_2026");
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashedId = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

      // 3. Store hashed ID and timestamp in Firestore
      await addDoc(collection(db, "downloads"), {
        hashed_user_id: hashedId,
        platform_downloaded: "pending", 
        authenticated_at: serverTimestamp()
      });

      // 4. Update UI state to show the download button
      setIsSignedIn(true);

    } catch (error) {
      console.error("Authentication or Database error:", error);
      alert("Failed to sign in. Please try again or check your popup blocker.");
    } finally {
      setIsAuthenticating(false);
    }
  };

  return (
    <div className="min-h-screen font-sans selection:bg-pink-200 selection:text-pink-900 pb-20 text-gray-800">
      
      {/* MoodPlay logo */}
      <nav className="flex justify-between items-center px-8 py-6 max-w-6xl mx-auto">
        <div className="flex items-center gap-2.5 text-2xl font-bold tracking-tight">
          <img src={logo} alt="MoodPlay Logo" className="w-8 h-8" />
          <div>
            <span className="text-[#E88DAC]">Mood</span>
            <span className="text-[#4F7BCA]">Play</span>
          </div>
        </div>
        
        {/* Sign-in pill */}
        <div className="flex items-center">
          {!isSignedIn ? (
            <button 
              onClick={initiateAuthFlow}
              disabled={isAuthenticating}
              className={`flex items-center gap-2 bg-white/80 hover:bg-white border border-gray-200 shadow-sm text-sm font-bold text-gray-700 py-2.5 px-5 rounded-full transition-all ${isAuthenticating ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md hover:-translate-y-0.5'}`}
            >
              {isAuthenticating ? (
                <span className="animate-pulse text-[#E88DAC]">Connecting...</span>
              ) : (
                <>
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                  Sign in
                </>
              )}
            </button>
          ) : (
            <a
              href="/MoodPlayInstaller.exe"
              download="MoodPlayInstaller.exe"
              className="flex items-center gap-2.5 bg-[#E88DAC] text-white shadow-sm text-sm font-bold py-2.5 px-5 rounded-full transition-all hover:opacity-90 hover:shadow-md transform hover:-translate-y-0.5 animate-in fade-in zoom-in duration-300"
            >
              <svg className="w-4 h-4 bg-white/20 rounded-full p-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Download (.exe)
            </a>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <header className="max-w-4xl mx-auto px-6 py-12 text-center flex flex-col items-center">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
          <span className="text-[#E88DAC]">Colorize videos.</span> <br /> 
          <span className="text-[#4F7BCA]">Give cinematic moods.</span>
        </h1>
        
        <p className="text-lg md:text-xl text-gray-600 mb-4 max-w-2xl leading-relaxed font-medium">
          Pick colors for people and things, then transform your entire video with a cinematic mood. From neon nights to warm sunsets, give your video a signature look in just one click.
        </p>
      </header>

      {/* Feature Grid */}
      <section className="max-w-5xl mx-auto px-6 py-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { icon: '🎯', title: 'Object Color Control', desc: 'Choose colors for each person or object, and watch them stay perfectly tracked.' },
          { icon: '🎬', title: 'No Flicker', desc: 'Your colors stay locked in: no jumping, no flickering, just clean visuals.' },
          { icon: '🌈', title: 'Mood Styles', desc: 'From neon nights to warm sunsets, give your video a signature look.' },
        ].map((feat, idx) => (
          <div key={idx} className="bg-white/40 backdrop-blur-md border border-white/60 shadow-lg p-8 rounded-3xl flex flex-col items-center text-center hover:bg-white/60 hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 cursor-default">
            <div className="text-4xl mb-4">{feat.icon}</div>
            <h4 className="text-lg font-extrabold text-gray-900 mb-2">{feat.title}</h4>
            <p className="text-sm text-gray-600 leading-relaxed font-medium">{feat.desc}</p>
          </div>
        ))}
      </section>

      {/* System Requirements Section */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        
        {/* Header */}
        <div className="text-center mb-10">
          <h2 className="text-3xl md:text-4xl font-extrabold mb-3 tracking-tight inline-block">
            <span className="text-[#E88DAC]">Ready to </span>
            <span className="text-[#4F7BCA]">create?</span>
          </h2>
          <p className="text-gray-600 font-medium">Review the system requirements to ensure compatibility.</p>
        </div>

        <div className="bg-white/40 backdrop-blur-md border border-white/60 shadow-lg rounded-3xl p-8 md:p-12 text-gray-800">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-6 flex items-center gap-3">
            <svg className="w-6 h-6 text-[#E88DAC]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            System Requirements
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b-2 border-white/60 text-gray-500 text-sm uppercase tracking-wider">
                  <th className="py-4 pr-4 font-bold whitespace-nowrap">Hardware</th>
                  <th className="py-4 px-4 font-bold">Minimum</th>
                  <th className="py-4 pl-4 font-bold">Recommended</th>
                </tr>
              </thead>
              <tbody className="text-sm md:text-base divide-y divide-white/40">
                <tr>
                  <td className="py-5 pr-4 font-bold text-gray-900">Operating System</td>
                  <td className="py-5 px-4 text-gray-700 font-medium">Windows 10/11</td>
                  <td className="py-5 pl-4 text-gray-700 font-medium">Windows 10/11</td>
                </tr>
                <tr>
                  <td className="py-5 pr-4 font-bold text-gray-900">Processor</td>
                  <td className="py-5 px-4 text-gray-700 font-medium">6 cores / 12 threads<br />
                    <span className="text-xs text-gray-500 font-medium">(NVIDIA GPU)</span>
                  </td>
                  <td className="py-5 pl-4 text-gray-700 font-medium">8–16 cores<br />
                    <span className="text-xs text-gray-500 font-medium">(NVIDIA GPU)</span>
                  </td>
                </tr>
                <tr>
                  <td className="py-5 pr-4 font-bold text-gray-900">RAM</td>
                  <td className="py-5 px-4 text-gray-700 font-medium">16 GB</td>
                  <td className="py-5 pl-4 text-gray-700 font-medium">32 GB</td>
                </tr>
                <tr>
                  <td className="py-5 pr-4 font-bold text-gray-900">GPU (VRAM)</td>
                  <td className="py-5 px-4 text-gray-700 font-medium">8 GB VRAM</td>
                  <td className="py-5 pl-4 text-gray-700 font-medium">16 GB VRAM</td>
                </tr>
                <tr>
                  <td className="py-5 pr-4 font-bold text-gray-900">Storage</td>
                  <td className="py-5 px-4 text-gray-700 leading-relaxed font-medium">
                    At least 80 GB available<br />space in SSD
                  </td>
                  <td className="py-5 pl-4 text-gray-700 leading-relaxed font-medium">
                    At least 100 GB available<br />space in SSD
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Terms of Service Modal */}
      {showTos && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
          <div className="bg-white border border-gray-100 rounded-3xl p-8 md:p-10 max-w-3xl w-full relative text-left shadow-2xl flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-300">
            <button 
              onClick={() => setShowTos(false)}
              className="absolute top-5 right-5 text-gray-400 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-full p-2 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
            
            <h2 className="text-3xl font-extrabold text-gray-900 mb-6 shrink-0">Terms & Privacy</h2>
            
            {/* Scrollable text container */}
            <div 
              onScroll={handleScroll}
              className="text-base text-gray-600 space-y-5 overflow-y-auto pr-4 font-medium flex-grow border-b border-gray-100 pb-6 mb-6"
            >
              <p className="text-gray-500 italic mb-4">Please scroll to the bottom to accept the terms and proceed with authentication.</p>
              <p><strong className="text-gray-900 text-lg">1. Purpose of Authentication</strong></p>
              <p>
                MoodPlay requires users to sign in via Google exclusively for the purpose of maintaining accurate download analytics and preventing automated abuse of our distribution endpoints. 
              </p>
              <p><strong className="text-gray-900 text-lg">2. Data Usage & Storage</strong></p>
              <p>
                We do not harvest, sell, or deeply analyze your personal data. The only information recorded in our database is:
              </p>
              <ul className="list-disc pl-6 space-y-2 text-gray-500">
                <li>Your Google Account ID (anonymized/hashed)</li>
                <li>Timestamp of login/download</li>
              </ul>
              <p>
                We do <strong className="text-gray-900">not</strong> have access to your passwords, your Google Drive files, or your contacts.
              </p>
              <p><strong className="text-gray-900 text-lg">3. App Usage</strong></p>
              <p>
                All video processing done within the MoodPlay application runs entirely on your local machine. No videos or images are sent to our servers for processing. By downloading this software, you agree to run it on compatible hardware as listed in the system requirements.
              </p>
              <p><strong className="text-gray-900 text-lg">4. Distribution</strong></p>
              <p>
                The executable files provided are for personal use. You may not repackage, sell, or distribute modified versions of the MoodPlay application without explicit consent.
              </p>
            </div>

            {/* Checkbox and Action Button Container */}
            <div className="shrink-0 flex flex-col gap-5">
              <div className={`transition-opacity duration-300 ${hasScrolledToBottom ? 'opacity-100' : 'opacity-30 pointer-events-none'}`}>
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input 
                    type="checkbox" 
                    checked={tosAccepted}
                    onChange={(e) => setTosAccepted(e.target.checked)}
                    className="mt-1 w-5 h-5 rounded border-gray-300 text-[#E88DAC] focus:ring-[#E88DAC] cursor-pointer"
                  />
                  <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition-colors">
                    I have scrolled, read, and understand the terms regarding data usage, local processing, and authentication requirements.
                  </span>
                </label>
              </div>

              <button 
                disabled={!tosAccepted}
                onClick={handleGoogleSignIn}
                className={`w-full py-4 rounded-xl font-bold text-lg transition-all transform flex items-center justify-center gap-3 ${
                  tosAccepted 
                    ? 'bg-[#E88DAC] text-white hover:opacity-90 hover:shadow-lg hover:-translate-y-0.5' 
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                {tosAccepted ? (
                  <>
                    <svg className="w-5 h-5 bg-white rounded-full p-0.5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Accept & Sign in with Google
                  </>
                ) : (
                  'Scroll to accept terms'
                )}
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}