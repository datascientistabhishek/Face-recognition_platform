import React, { useState, useEffect, useRef } from 'react';

export default function ChatWidget(){
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const wsRef = useRef(null);
  const [waiting, setWaiting] = useState(false);

  useEffect(()=>{
    wsRef.current = new WebSocket('ws://localhost:3001');
    wsRef.current.onmessage = (ev) => {
      try{
        const d = JSON.parse(ev.data);
        if(d.type === 'chat_response'){
          // Handle both payload and direct response structures
          const answer = d.payload?.answer || d.answer || (d.error ? `Error: ${d.error}` : 'No response');
          setMessages(prev => {
            const last = prev[prev.length-1];
            if (last && last.from === 'bot' && last.text === '...'){
              // replace last
              return [...prev.slice(0, -1), {from:'bot', text: answer}];
            }
            return [...prev, {from:'bot', text: answer}];
          });
          setWaiting(false);
        }
      }catch(e){console.error(e)}
    }
    return ()=> wsRef.current && wsRef.current.close();
  },[])

  const send = () => {
    if (!input || waiting) return;
    setMessages(m=>[...m, {from:'user', text: input}]);
    // add bot placeholder
    setMessages(m=>[...m, {from:'bot', text: '...'}]);
    setWaiting(true);
    wsRef.current.send(JSON.stringify({ type: 'chat', query: input }));
    setInput('');
  }

  return (
    <div className="chatBox">
      <div className="messages panel" id="messages">
        {messages.map((m,i)=> (
          <div key={i} className={"msg "+(m.from==='user'? 'user':'bot')}>
            <b style={{display:'block',marginBottom:6}}>{m.from}</b>
            <div>{m.text}</div>
          </div>
        ))}
        {waiting && <div className="typing">Bot is typing...</div>}
      </div>
      <div className="inputRow">
        <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask about registrations..." disabled={waiting} />
        <button className="btn" onClick={send} disabled={waiting || !input}>Send</button>
      </div>
    </div>
  )
}
