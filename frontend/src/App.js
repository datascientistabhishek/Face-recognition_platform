import React, { useState } from 'react';
import RegistrationTab from './components/RegistrationTab';
import LiveRecognitionTab from './components/LiveRecognitionTab';
import ChatWidget from './components/ChatWidget';

export default function App(){
  const [tab, setTab] = useState('register');
  return (
    <div className="app">
      <div className="header">
        <div className="title">Face Recognition Platform</div>
        <div className="nav">
          <button className={tab==='register'? 'active':''} onClick={()=>setTab('register')}>Registration</button>
          <button className={tab==='live'? 'active':''} onClick={()=>setTab('live')}>Live Recognition</button>
          <button className={tab==='chat'? 'active':''} onClick={()=>setTab('chat')}>Chat</button>
        </div>
      </div>
      <div className="layout">
        <div className="panel">
          {tab === 'register' && <RegistrationTab />}
          {tab === 'live' && <LiveRecognitionTab />}
          {tab === 'chat' && <ChatWidget />}
        </div>
        <div className="panel">
          <div className="small">Quick Info</div>
          <div className="metaList">
            <div className="metaItem">Server: Node proxy on <code>:3001</code></div>
            <div className="metaItem">Face service: <code>:8001</code></div>
            <div className="metaItem">RAG service: <code>:8002</code></div>
          </div>
        </div>
      </div>
    </div>
  )
}
