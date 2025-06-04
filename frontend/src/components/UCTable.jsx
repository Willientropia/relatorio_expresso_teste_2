import { useState } from 'react';
import ActionButton from './ActionButton';
import InputField from './InputField';

const UCTable = ({ ucs, onAddUc, onDeleteUc }) => {
  const [newUc, setNewUc] = useState({
    codigo: '',
    endereco: '',
    tipo: 'Residencial'
  });

  const handleSubmit = () => {
    if (newUc.codigo && newUc.endereco) {
      onAddUc(newUc);
      setNewUc({
        codigo: '',
        endereco: '',
        tipo: 'Residencial'
      });
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Adicionar Nova UC</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código</label>
            <InputField
              value={newUc.codigo}
              onChange={(value) => setNewUc({...newUc, codigo: value})}
              placeholder="Unidade Consumidora"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
            <InputField
              value={newUc.endereco}
              onChange={(value) => setNewUc({...newUc, endereco: value})}
              placeholder="Endereço da UC"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
            <select
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              value={newUc.tipo}
              onChange={(e) => setNewUc({...newUc, tipo: e.target.value})}
            >
              <option value="Residencial">Residencial</option>
              <option value="Comercial">Comercial</option>
              <option value="Industrial">Industrial</option>
              <option value="Rural">Rural</option>
            </select>
          </div>
        </div>
        <ActionButton icon="plus" onClick={handleSubmit}>
          Adicionar UC
        </ActionButton>
      </div>
      
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Unidades Consumidoras</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-hashtag mr-1"></i> Unidade Consumidora
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-map-marker-alt mr-1"></i> Endereço
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-tag mr-1"></i> Tipo
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-cog mr-1"></i> Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {ucs.map((uc) => (
              <tr key={uc.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {uc.codigo}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {uc.endereco}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${uc.tipo === 'Residencial' ? 'bg-green-100 text-green-800' : 
                      uc.tipo === 'Comercial' ? 'bg-blue-100 text-blue-800' : 
                      uc.tipo === 'Industrial' ? 'bg-purple-100 text-purple-800' : 
                      'bg-yellow-100 text-yellow-800'}`}>
                    {uc.tipo}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteUc(uc.id);
                    }}
                    className="text-red-600 hover:text-red-900 mr-3"
                    title="Excluir"
                  >
                    <i className="fas fa-trash-alt"></i>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      console.log('Edit UC:', uc.id);
                    }}
                    className="text-indigo-600 hover:text-indigo-900"
                    title="Editar"
                  >
                    <i className="fas fa-edit"></i>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UCTable;
