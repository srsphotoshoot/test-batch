import React from "react";

const Sidebar = ({ setCurrentView }) => {

  return (
    <div className="sidebar">

      <div className="logo">
        <img src="/2.png" alt="SRS Logo" className="sidebar-logo" />
      </div>

      <nav>

        <button onClick={() => setCurrentView("list")}>
          Dashboard
        </button>

        <button onClick={() => setCurrentView("create")}>
          Create Batch
        </button>

        <button onClick={() => setCurrentView("list")}>
          Batch History
        </button>

      </nav>

    </div>
  );

};

export default Sidebar;
