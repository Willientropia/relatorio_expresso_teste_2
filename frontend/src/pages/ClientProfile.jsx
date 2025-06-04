import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import ClientInfoCard from '../components/ClientInfoCard';
import TabNavigation from '../components/TabNavigation';
import UCTable from '../components/UCTable';
import EmptyState from '../components/EmptyState';
import ActionButton from '../components/ActionButton';

function ClientProfile() {
  const [client, setClient] = useState(null);
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState('uc');
  const [ucs, setUcs] = useState([]);

  useEffect(() => {
    // Fetch client data
    fetch(`/api/customers/${id}/`)
      .then(response => response.json())
      .then(data => setClient(data))
      .catch(error => console.error('Error:', error));

    // Fetch UCs data (to be implemented in the backend)
    setUcs([
      { id: 1, codigo: 'UC001', endereco: 'Rua das Flores, 123 - Centro, São Paulo/SP', tipo: 'Residencial' },
      { id: 2, codigo: 'UC002', endereco: 'Avenida Brasil, 456 - Jardins, São Paulo/SP', tipo: 'Comercial' },
      { id: 3, codigo: 'UC003', endereco: 'Rua dos Pinheiros, 789 - Pinheiros, São Paulo/SP', tipo: 'Industrial' }
    ]);
  }, [id]);

  const handleAddUc = (newUc) => {
    setUcs([...ucs, { ...newUc, id: Date.now() }]);
  };

  const handleDeleteUc = (id) => {
    setUcs(ucs.filter(uc => uc.id !== id));
  };

  if (!client) {
    return (
      <div className="min-h-screen p-4 md:p-8 flex items-center justify-center">
        <div className="text-center">
          <i className="fas fa-spinner fa-spin text-4xl text-indigo-600 mb-4"></i>
          <p className="text-gray-600">Carregando dados do cliente...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Perfil do Cliente</h1>
        
        <ClientInfoCard client={client} onEdit={() => console.log('Edit client')} />
        
        <div className="bg-white rounded-xl shadow-md overflow-hidden mt-6">
          <TabNavigation
            activeTab={activeTab}
            onTabChange={setActiveTab}
            tabs={[
              { id: 'uc', label: 'Unidades Consumidoras' },
              { id: 'documents', label: 'Documentos', icon: 'file' },
              { id: 'invoices', label: 'Faturas', icon: 'file-invoice-dollar' },
              { id: 'utility', label: 'Concessionária', icon: 'building' },
              { id: 'history', label: 'Histórico', icon: 'history' }
            ]}
          />
          
          <div className="p-6">
            {activeTab === 'uc' && (
              <UCTable
                ucs={ucs}
                onAddUc={handleAddUc}
                onDeleteUc={handleDeleteUc}
              />
            )}
            
            {activeTab === 'documents' && (
              <EmptyState
                icon="file-alt"
                title="Documentos do cliente"
                description="Adicione documentos como contratos, faturas e comprovantes nesta seção."
                action={
                  <ActionButton
                    icon="plus"
                    onClick={() => console.log('Add document')}
                  >
                    Adicionar Documento
                  </ActionButton>
                }
              />
            )}
            
            {activeTab === 'history' && (
              <EmptyState
                icon="history"
                title="Histórico do cliente"
                description="Visualize o histórico de consumo, pagamentos e interações com o cliente."
                action={
                  <ActionButton
                    icon="chart-line"
                    onClick={() => console.log('View charts')}
                  >
                    Ver Gráficos
                  </ActionButton>
                }
              />
            )}

            {activeTab === 'utility' && (
              <EmptyState
                icon="building"
                title="Concessionária"
                description="Gerencie a integração com a concessionária de energia."
                action={
                  <ActionButton
                    icon="file-import"
                    onClick={() => console.log('Import invoices')}
                  >
                    Importar Faturas em aberto
                  </ActionButton>
                }
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ClientProfile;
