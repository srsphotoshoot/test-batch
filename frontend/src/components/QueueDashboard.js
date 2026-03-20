// import React from 'react';

// const QueueDashboard = ({ status }) => {
//     const isProcessing = status.generating > 0;

//     return (
//         <div className="queue-dashboard">
//             <div className={`status-pill ${isProcessing ? 'processing' : 'idle'}`}>
//                 <span className="dot"></span>
//                 {isProcessing ? 'System Processing' : 'System Idle'}
//             </div>
//             <div className="stats">
//                 <div className="stat-item">
//                     <span className="label">Queued Batches:</span>
//                     <span className="value">{status.queued}</span>
//                 </div>
//                 {isProcessing && (
//                     <div className="stat-item highlight">
//                         <span className="label">Active:</span>
//                         <span className="value">1</span>
//                     </div>
//                 )}
//             </div>
//             <style jsx>{`
//         .queue-dashboard {
//           background: rgba(10, 10, 15, 0.8);
//           border: 1px solid rgba(0, 255, 255, 0.2);
//           border-radius: 12px;
//           padding: 15px 25px;
//           margin-bottom: 25px;
//           display: flex;
//           align-items: center;
//           justify-content: space-between;
//           backdrop-filter: blur(10px);
//           box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
//         }
//         .status-pill {
//           display: flex;
//           align-items: center;
//           gap: 10px;
//           padding: 5px 15px;
//           border-radius: 20px;
//           font-size: 0.9rem;
//           font-weight: 600;
//           text-transform: uppercase;
//         }
//         .status-pill.idle {
//           background: rgba(0, 255, 127, 0.1);
//           color: #00ff7f;
//           border: 1px solid rgba(0, 255, 127, 0.3);
//         }
//         .status-pill.processing {
//           background: rgba(255, 0, 255, 0.1);
//           color: #ff00ff;
//           border: 1px solid rgba(255, 0, 255, 0.3);
//         }
//         .dot {
//           width: 8px;
//           height: 8px;
//           border-radius: 50%;
//           background: currentColor;
//           box-shadow: 0 0 10px currentColor;
//         }
//         .processing .dot {
//           animation: pulse 1.5s infinite;
//         }
//         @keyframes pulse {
//           0% { transform: scale(1); opacity: 1; }
//           50% { transform: scale(1.5); opacity: 0.5; }
//           100% { transform: scale(1); opacity: 1; }
//         }
//         .stats {
//           display: flex;
//           gap: 30px;
//         }
//         .stat-item {
//           display: flex;
//           flex-direction: column;
//           align-items: flex-end;
//         }
//         .label {
//           color: rgba(255, 255, 255, 0.5);
//           font-size: 0.75rem;
//           text-transform: uppercase;
//           letter-spacing: 1px;
//         }
//         .value {
//           color: #fff;
//           font-size: 1.2rem;
//           font-weight: 700;
//           font-family: 'JetBrains Mono', monospace;
//         }
//         .highlight .value {
//           color: #00ffff;
//           text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
//         }
//       `}</style>
//         </div>
//     );
// };

// export default QueueDashboard;
import React from 'react';

const QueueDashboard = ({ status }) => {

  const isProcessing = status.generating > 0;
  const totalJobs = status.queued + status.generating;

  return (
    <div className="queue-dashboard">

      <div className={`status-pill ${isProcessing ? 'processing' : 'idle'}`}>
        <span className="dot"></span>
        {isProcessing ? 'System Processing' : 'System Idle'}
      </div>

      <div className="stats">

        <div className="stat-item">
          <span className="label">Queued Batches</span>
          <span className="value">{status.queued}</span>
        </div>

        <div className="stat-item">
          <span className="label">Generating</span>
          <span className="value">{status.generating}</span>
        </div>

        <div className="stat-item highlight">
          <span className="label">Total Jobs</span>
          <span className="value">{totalJobs}</span>
        </div>

      </div>

<style jsx>{`

.queue-dashboard{
  background:rgba(10,10,15,0.85);
  border:1px solid rgba(0,255,255,0.2);
  border-radius:12px;
  padding:16px 25px;
  margin-bottom:25px;

  display:flex;
  align-items:center;
  justify-content:space-between;

  backdrop-filter:blur(10px);

  box-shadow:
  0 6px 25px rgba(0,0,0,0.6),
  0 0 20px rgba(0,255,255,0.05);

  transition:all .3s ease;
}

.queue-dashboard:hover{
  transform:translateY(-2px);
  box-shadow:
  0 10px 35px rgba(0,0,0,0.8),
  0 0 25px rgba(0,255,255,0.15);
}

/* STATUS PILL */

.status-pill{
  display:flex;
  align-items:center;
  gap:10px;
  padding:6px 16px;

  border-radius:20px;

  font-size:.85rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:.5px;
}

.status-pill.idle{
  background:rgba(0,255,127,0.1);
  color:#00ff7f;
  border:1px solid rgba(0,255,127,0.3);
}

.status-pill.processing{
  background:rgba(255,0,255,0.1);
  color:#ff00ff;
  border:1px solid rgba(255,0,255,0.3);
}

/* DOT */

.dot{
  width:8px;
  height:8px;
  border-radius:50%;
  background:currentColor;
  box-shadow:0 0 10px currentColor;
}

.processing .dot{
  animation:pulse 1.4s infinite;
}

@keyframes pulse{
  0%{transform:scale(1);opacity:1;}
  50%{transform:scale(1.6);opacity:.4;}
  100%{transform:scale(1);opacity:1;}
}

/* STATS */

.stats{
  display:flex;
  gap:35px;
}

.stat-item{
  display:flex;
  flex-direction:column;
  align-items:flex-end;
}

.label{
  color:rgba(255,255,255,0.5);
  font-size:.7rem;
  text-transform:uppercase;
  letter-spacing:1px;
}

.value{
  color:#fff;
  font-size:1.3rem;
  font-weight:700;
  font-family:'JetBrains Mono', monospace;
  transition:all .3s ease;
}

.stat-item:hover .value{
  color:#00ffff;
  text-shadow:0 0 10px rgba(0,255,255,.6);
}

.highlight .value{
  color:#00ffff;
  text-shadow:0 0 10px rgba(0,255,255,.4);
}

/* RESPONSIVE */

@media(max-width:700px){

.queue-dashboard{
  flex-direction:column;
  align-items:flex-start;
  gap:12px;
}

.stats{
  width:100%;
  justify-content:space-between;
}

}

`}</style>

    </div>
  );
};

export default QueueDashboard;

