const TabNavigation = ({ activeTab, onTabChange, tabs }) => {
  return (
    <div className="border-b border-gray-200">
      <nav className="flex -mb-px">
        {tabs.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === id
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {icon && <i className={`fas fa-${icon} mr-1`}></i>}
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
};

export default TabNavigation;
