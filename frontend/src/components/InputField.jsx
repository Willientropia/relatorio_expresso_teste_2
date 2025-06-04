const InputField = ({ placeholder, value, onChange }) => {
  return (
    <input
      type="text"
      placeholder={placeholder}
      className="p-2 border rounded"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
};

export default InputField;
