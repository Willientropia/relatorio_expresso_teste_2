import ActionButton from './ActionButton';

const ClientInfoCard = ({ client, onEdit }) => {
  const infoItems = [
    { label: 'CPF', value: client?.cpf || 'N/A' },
    { label: 'Endereço', value: client?.endereco || 'N/A' },
    { label: 'Telefone', value: client?.telefone || 'N/A' },
    { label: 'E-mail', value: client?.email || 'N/A' }
  ];

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="p-6">
        <div className="flex items-center mb-4">
          <div className="bg-indigo-100 p-3 rounded-full mr-4">
            <i className="fas fa-user text-indigo-600 text-2xl"></i>
          </div>
          <h2 className="text-2xl font-semibold text-gray-800">{client.nome}</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {infoItems.map(({ label, value }) => (
            <div key={label} className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-gray-500 mb-1">{label}</h3>
              <p className="font-medium">{value}</p>
            </div>
          ))}
        </div>
      </div>
      
      <div className="bg-gray-50 px-6 py-4 flex justify-end items-center">
        <ActionButton icon="edit" onClick={onEdit}>
          Editar Perfil
        </ActionButton>
      </div>
    </div>
  );
};

export default ClientInfoCard;
