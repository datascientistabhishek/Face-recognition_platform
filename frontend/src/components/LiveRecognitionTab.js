import React, { useRef, useEffect, useState } from 'react';

export default function LiveRecognitionTab(){
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const captureIntervalRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [wsStatus, setWsStatus] = useState('disconnected');

  useEffect(()=>{
    wsRef.current = new WebSocket('ws://localhost:3001');
    
    wsRef.current.onopen = () => {
      setWsStatus('connected');
      addLog('WebSocket connected');
    };
    
    wsRef.current.onmessage = (ev) => {
      try{
        const d = JSON.parse(ev.data);
        console.log('Received message:', d);
        if(d.type === 'recognition'){
          addLog(`Recognition: ${JSON.stringify(d.payload)}`);
        } else if (d.error) {
          addLog(`Error: ${d.error}`);
        }
      }catch(e){
        console.error('Error parsing message:', e);
        addLog(`Parse error: ${e.message}`);
      }
    };
    
    wsRef.current.onerror = (err) => {
      setWsStatus('error');
      addLog(`WebSocket error: ${err.message || 'Unknown error'}`);
      console.error('WebSocket error:', err);
    };
    
    wsRef.current.onclose = () => {
      setWsStatus('disconnected');
      addLog('WebSocket disconnected');
    };
    
    return ()=>{
      if (wsRef.current) {
        try{ wsRef.current.close(); }catch(e){}
      }
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
      }
      // stop video tracks
      if (videoRef.current && videoRef.current.srcObject){
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(t=>t.stop());
      }
    };
  },[]);

  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(l => [`[${timestamp}] ${message}`, ...l].slice(0, 20));
  };

  const start = async () => {
    try{
      addLog('Starting video stream...');
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (!videoRef.current) return;
      videoRef.current.srcObject = stream;
      addLog('Video stream obtained');

      // Wait for video metadata so videoWidth/videoHeight are available
      await new Promise((resolve) => {
        if (videoRef.current.readyState >= 1 && videoRef.current.videoWidth > 0) {
          resolve(true);
        } else {
          const onLoaded = () => {
            videoRef.current.removeEventListener('loadedmetadata', onLoaded);
            resolve(true);
          };
          videoRef.current.addEventListener('loadedmetadata', onLoaded);
        }
      });

      videoRef.current.play();
      addLog(`Video playing (${videoRef.current.videoWidth}x${videoRef.current.videoHeight})`);
      setIsRunning(true);

      // capture frames at ~1 fps
      captureIntervalRef.current = setInterval(async ()=>{
        try{
          if (!videoRef.current) return;
          const w = videoRef.current.videoWidth || videoRef.current.clientWidth;
          const h = videoRef.current.videoHeight || videoRef.current.clientHeight;
          if (!w || !h) {
            addLog('Video dimensions not ready');
            return;
          }
          const canvas = document.createElement('canvas');
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(videoRef.current,0,0,w,h);
          const data = canvas.toDataURL('image/jpeg', 0.7);
          if (wsRef.current && wsRef.current.readyState === 1) {
            console.log('Sending frame to server');
            wsRef.current.send(JSON.stringify({ type: 'frame', image: data }));
          } else {
            addLog(`WebSocket not ready: state=${wsRef.current?.readyState}`);
          }
        }catch(e){
          console.error('Capture error', e);
          addLog(`Capture error: ${e.message}`);
        }
      }, 1000);
    }catch(e){
      console.error('Could not start video stream', e);
      addLog(`Error starting video: ${e.message}`);
      setIsRunning(false);
    }
  };

  const stop = () => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    if (videoRef.current && videoRef.current.srcObject){
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(t=>t.stop());
    }
    setIsRunning(false);
    addLog('Stopped video stream');
  };

  return (
    <div className="videoWrap">
      <div className="videoBox">
        <video ref={videoRef} style={{ width: '100%', height: '100%', background: '#000' }} />
      </div>
      <div className="controls">
        <button className="btn" onClick={start} disabled={isRunning}>Start Live</button>
        <button className="btn" onClick={stop} disabled={!isRunning} style={{marginLeft: 8}}>Stop Live</button>
        <span style={{marginLeft: 12}}>WS Status: <strong>{wsStatus}</strong></span>
      </div>
      <div style={{ maxHeight: 200, overflow: 'auto', marginTop: 12 }}>
        <h4>Recognition Events</h4>
        <ul>
          {logs.map((l,i)=>(<li key={i}><pre style={{whiteSpace:'pre-wrap', fontSize: '12px', margin: '2px 0'}}>{l}</pre></li>))}
        </ul>
      </div>
    </div>
  )
}
