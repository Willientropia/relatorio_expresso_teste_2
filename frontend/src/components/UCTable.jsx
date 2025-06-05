import { useState } from 'react';
import ActionButton from './ActionButton';
import InputField from './InputField';
import EmptyState from './EmptyState';

const UCTable = ({ ucs, onAddUc, onDeleteUc, onToggleStatus, onEditUc }) => {
  const [activeTab, setActiveTab] = useState('active');
  const [newUc, setNewUc] = useState({
    codigo: '',
    endereco: '',
    tipo: 'Residencial',
    data_vigencia_inicio: new Date().toISOString().split('T')[0]
  });
  const [editingUc, setEditingUc] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);

  const activeUcs = ucs.filter(uc => uc.is_active);
  const inactiveUcs = ucs.filter(uc => !uc.is_active);

  const handleSubmit = () => {
    if (newUc.codigo && newUc.endereco && newUc.data_vigencia_inicio) {
      onAddUc(newUc);
      setNewUc({
        codigo: '',
        endereco: '',
        tipo: 'Residencial',
        data_vigencia_inicio: new Date().toISOString().split('T')[0]
      });
    }
  };

  const handleEdit = (uc) => {
    setEditingUc({...uc});
    setShowEditModal(true);
  };

  const handleSaveEdit = () => {
    if (editingUc && editingUc.codigo && editingUc.endereco) {
      onEditUc(editingUc);
      setShowEditModal(false);
      setEditingUc(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
  };

  const renderUCTable = (ucList, isActive) => {
    if (ucList.length === 0) {
      return (
        <EmptyState
          icon={isActive ? "plug" : "power-off"}
          title={isActive ? "Nenhuma UC ativa" : "Nenhuma UC inativa"}
          description={isActive ? 
            "Adicione unidades consumidoras usando o formulário acima." : 
            "UCs inativas aparecerão aqui."}
        />
      );
    }

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-hashtag mr-1"></i> Código UC
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-map-marker-alt mr-1"></i> Endereço
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-tag mr-1"></i> Tipo
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-calendar-check mr-1"></i> Início Vigência
              </th>
              {!isActive && (
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <i className="fas fa-calendar-times mr-1"></i> Fim Vigência
                </th>
              )}
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                <i className="fas fa-cog mr-1"></i> Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {ucList.map((uc) => (
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
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(uc.data_vigencia_inicio)}
                </td>
                {!isActive && (
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(uc.data_vigencia_fim)}
                  </td>
                )}
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => handleEdit(uc)}
                    className="text-indigo-600 hover:text-indigo-900 mr-3"
                    title="Editar"
                  >
                    <i className="fas fa-edit"></i>
                  </button>
                  
                  <button
                    onClick={() => onToggleStatus(uc.id)}
                    className={`${isActive ? 'text-orange-600 hover:text-orange-900' : 'text-green-600 hover:text-green-900'} mr-3`}
                    title={isActive ? "Desativar" : "Reativar"}
                  >
                    <i className={`fas fa-${isActive ? 'power-off' : 'plug'}`}></i>
                  </button>
                  
                  {!isActive && (
                    <button
                      onClick={() => onDeleteUc(uc.id)}
                      className="text-red-600 hover:text-red-900"
                      title="Excluir"
                    >
                      <i className="fas fa-trash-alt"></i>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      {/* Formulário de cadastro */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Adicionar Nova UC</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código UC</label>
            <InputField
              value={newUc.codigo}
              onChange={(value) => setNewUc({...newUc, codigo: value})}
              placeholder="Ex: UC001"
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
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data Início Vigência</label>
            <input
              type="date"
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              value={newUc.data_vigencia_inicio}
              onChange={(e) => setNewUc({...newUc, data_vigencia_inicio: e.target.value})}
            />
          </div>
        </div>
        <ActionButton icon="plus" onClick={handleSubmit}>
          Adicionar UC
        </ActionButton>
      </div>
      
      {/* Tabs */}
      <div className="border-b border-gray-200 mb-4">
        <nav className="flex -mb-px">
          <button
            onClick={() => setActiveTab('active')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'active'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-plug mr-1"></i>
            Ativas ({activeUcs.length})
          </button>
          <button
            onClick={() => setActiveTab('inactive')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'inactive'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-power-off mr-1"></i>
            Inativas ({inactiveUcs.length})
          </button>
        </nav>
      </div>
      
      {/* Tabelas */}
      {activeTab === 'active' ? renderUCTable(activeUcs, true) : renderUCTable(inactiveUcs, false)}
      
      {/* Modal de Edição */}
      {showEditModal && editingUc && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Editar UC</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Código UC</label>
                <InputField
                  value={editingUc.codigo}
                  onChange={(value) => setEditingUc({...editingUc, codigo: value})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
                <InputField
                  value={editingUc.endereco}
                  onChange={(value) => setEditingUc({...editingUc, endereco: value})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select
                  className="w-full p-2 border border-gray-300 rounded-md"
                  value={editingUc.tipo}
                  onChange={(e) => setEditingUc({...editingUc, tipo: e.target.value})}
                >
                  <option value="Residencial">Residencial</option>
                  <option value="Comercial">Comercial</option>
                  <option value="Industrial">Industrial</option>
                  <option value="Rural">Rural</option>
                </select>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end space-x-3">
              <ActionButton
                variant="secondary"
                onClick={() => {
                  setShowEditModal(false);
                  setEditingUc(null);
                }}
              >
                Cancelar
              </ActionButton>
              <ActionButton onClick={handleSaveEdit}>
                Salvar
              </ActionButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UCTable;