// frontend/src/components/FaturaImport.jsx
import { useState, useEffect } from 'react';
import ActionButton from './ActionButton';
import EmptyState from './EmptyState';

const FaturaImport = ({ customerId }) => {
  const [tasks, setTasks] = useState([]);
  const [faturas, setFaturas] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [activeTab, setActiveTab] = useState('faturas');

  // Busca tarefas em andamento
  const fetchTasks = async () => {
    try {
      const response = await fetch(`/api/customers/${customerId}/faturas/tasks/`);
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
        
        // Verifica se há tarefas em andamento
        const hasActiveTask = data.some(task => 
          task.status === 'pending' || task.status === 'processing'
        );
        setImporting(hasActiveTask);
      }
    } catch (error) {
      console.error('Erro ao buscar tarefas:', error);
    }
  };

  // Busca faturas baixadas
  const fetchFaturas = async () => {
    try {
      const response = await fetch(`/api/customers/${customerId}/faturas/`);
      if (response.ok) {
        const data = await response.json();
        setFaturas(data);
      }
    } catch (error) {
      console.error('Erro ao buscar faturas:', error);
    }
  };

  // Busca logs
  const fetchLogs = async () => {
    try {
      const response = await fetch(`/api/customers/${customerId}/faturas/logs/`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (error) {
      console.error('Erro ao buscar logs:', error);
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchFaturas();
    fetchLogs();

    // Atualiza a cada 5 segundos se houver importação em andamento
    const interval = setInterval(() => {
      if (importing) {
        fetchTasks();
        fetchFaturas();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [customerId, importing]);

  const handleStartImport = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/customers/${customerId}/faturas/import/`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        alert('Importação iniciada com sucesso!');
        setImporting(true);
        fetchTasks();
      } else {
        const error = await response.json();
        alert(`Erro: ${error.error || 'Não foi possível iniciar a importação'}`);
      }
    } catch (error) {
      console.error('Erro ao iniciar importação:', error);
      alert('Erro ao iniciar importação');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'pending':
        return 'Pendente';
      case 'processing':
        return 'Processando';
      case 'completed':
        return 'Concluída';
      case 'failed':
        return 'Falhou';
      default:
        return status;
    }
  };

  const renderTasks = () => {
    if (tasks.length === 0) {
      return (
        <EmptyState
          icon="tasks"
          title="Nenhuma tarefa de importação"
          description="Clique em 'Importar Faturas em aberto' para iniciar"
        />
      );
    }

    return (
      <div className="space-y-4">
        {tasks.map((task) => (
          <div key={task.id} className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">
                  UC: {task.unidade_consumidora_codigo}
                </h4>
                <p className="text-sm text-gray-500">
                  Criada em: {new Date(task.created_at).toLocaleString('pt-BR')}
                </p>
                {task.error_message && (
                  <p className="text-sm text-red-600 mt-1">
                    Erro: {task.error_message}
                  </p>
                )}
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(task.status)}`}>
                {getStatusText(task.status)}
              </span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderFaturas = () => {
    if (faturas.length === 0) {
      return (
        <EmptyState
          icon="file-invoice-dollar"
          title="Nenhuma fatura baixada"
          description="As faturas aparecerão aqui após a importação"
        />
      );
    }

    // Agrupa faturas por UC
    const faturasByUC = faturas.reduce((acc, fatura) => {
      const uc = fatura.unidade_consumidora;
      if (!acc[uc]) {
        acc[uc] = [];
      }
      acc[uc].push(fatura);
      return acc;
    }, {});

    return (
      <div className="space-y-6">
        {Object.entries(faturasByUC).map(([uc, ucFaturas]) => (
          <div key={uc} className="bg-white p-6 rounded-lg border border-gray-200">
            <h4 className="font-medium text-gray-900 mb-4">
              UC: {ucFaturas[0].unidade_consumidora}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ucFaturas.map((fatura) => (
                <div key={fatura.id} className="bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">
                      {fatura.mes_referencia}
                    </span>
                    <i className="fas fa-file-pdf text-red-500"></i>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Baixada em: {new Date(fatura.downloaded_at).toLocaleDateString('pt-BR')}</p>
                    {fatura.valor && <p>Valor: R$ {fatura.valor}</p>}
                  </div>
                  <a
                    href={fatura.arquivo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex items-center text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    <i className="fas fa-download mr-1"></i>
                    Baixar PDF
                  </a>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderLogs = () => {
    if (logs.length === 0) {
      return (
        <EmptyState
          icon="history"
          title="Nenhum log de busca"
          description="Os logs de busca aparecerão aqui após as importações"
        />
      );
    }

    return (
      <div className="space-y-4">
        {logs.map((log) => (
          <div key={log.id} className="bg-white p-4 rounded-lg border border-gray-200">
            <div className="mb-2">
              <span className="text-sm text-gray-500">
                {new Date(log.created_at).toLocaleString('pt-BR')}
              </span>
              <p className="font-medium text-gray-900">
                CPF Titular: {log.cpf_titular}
              </p>
            </div>
            <div className="text-sm text-gray-600">
              <p>UCs encontradas: {log.ucs_encontradas.join(', ')}</p>
              <details className="mt-2">
                <summary className="cursor-pointer text-indigo-600 hover:text-indigo-800">
                  Ver detalhes das faturas
                </summary>
                <pre className="mt-2 bg-gray-50 p-2 rounded text-xs overflow-x-auto">
                  {JSON.stringify(log.faturas_encontradas, null, 2)}
                </pre>
              </details>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      {/* Botão de importar */}
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">
          Gerenciamento de Faturas
        </h3>
        <ActionButton
          icon="file-import"
          onClick={handleStartImport}
          disabled={loading || importing}
        >
          {importing ? 'Importação em andamento...' : 'Importar Faturas em aberto'}
        </ActionButton>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-4">
        <nav className="flex -mb-px">
          <button
            onClick={() => setActiveTab('faturas')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'faturas'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-file-invoice-dollar mr-1"></i>
            Faturas Baixadas ({faturas.length})
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'tasks'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-tasks mr-1"></i>
            Tarefas ({tasks.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'logs'
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <i className="fas fa-history mr-1"></i>
            Logs ({logs.length})
          </button>
        </nav>
      </div>

      {/* Conteúdo */}
      <div className="mt-4">
        {activeTab === 'faturas' && renderFaturas()}
        {activeTab === 'tasks' && renderTasks()}
        {activeTab === 'logs' && renderLogs()}
      </div>
    </div>
  );
};

export default FaturaImport;