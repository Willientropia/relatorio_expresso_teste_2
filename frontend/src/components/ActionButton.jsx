const ActionButton = ({ children, icon, onClick, variant = 'primary' }) => {
  const baseClasses = "px-4 py-2 rounded-md transition flex items-center";
  const variants = {
    primary: "bg-indigo-600 hover:bg-indigo-700 text-white",
    danger: "bg-red-600 hover:bg-red-700 text-white",
    secondary: "bg-gray-200 hover:bg-gray-300 text-gray-800"
  };

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${variants[variant]}`}
    >
      {icon && <i className={`fas fa-${icon} mr-2`}></i>}
      {children}
    </button>
  );
};

export default ActionButton;
