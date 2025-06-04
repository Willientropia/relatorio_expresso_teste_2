const EmptyState = ({ icon, title, description, action }) => {
  return (
    <div className="text-center py-12">
      <i className={`fas fa-${icon} text-4xl text-gray-300 mb-4`}></i>
      <h3 className="text-lg font-medium text-gray-600">{title}</h3>
      <p className="text-gray-500 mt-2">{description}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
};

export default EmptyState;
