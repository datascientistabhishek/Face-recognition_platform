import React, { useRef, useState, useEffect } from 'react';

export default function RegistrationTab(){
  const videoRef = useRef(null);
  const [name, setName] = useState('');
  const [status, setStatus] = useState('');
  const [recent, setRecent] = useState([]);

  useEffect(()=>{fetchRecent();},[])

  const fetchRecent = async ()=>{
    try{
      const r = await fetch('http://localhost:3001/api/metadata/last-registered').then(r=>r.json());
      setRecent(r);
    }catch(e){}
  }

  const startCamera = async () => {
    try{
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    }catch(e){console.error(e)}
  }

  const captureAndRegister = async () => {
    if (!videoRef.current) return setStatus('No camera');
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL('image/jpeg');
    setStatus('Registering...');
    const res = await fetch('http://localhost:3001/register', { // proxy via server
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, image: data })
    }).then(r=>r.json()).catch(e=>({error: e.message}));
    setStatus(JSON.stringify(res));
    await fetchRecent();
  }

  return (
    <div>
      <div className="videoWrap">
        <div className="videoBox">
          <video ref={videoRef} style={{ width: '100%', height: '100%', background: '#000' }} />
        </div>
        <div className="controls">
          <button className="btn" onClick={startCamera}>Start Camera</button>
          <input placeholder="Name" value={name} onChange={e=>setName(e.target.value)} />
          <button className="btn" onClick={captureAndRegister}>Capture & Register</button>
        </div>
      </div>
      <div className="small">Status: {status}</div>
      <div className="metaList">
        <div className="metaItem small">Last registered: {recent.name ? `${recent.name}` : 'none'}</div>
      </div>
    </div>
  )
}
