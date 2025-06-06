// frontend/src/App.jsx
import { useState, useEffect } from 'react'
import CustomerTable from './components/CustomerTable'
import InputField from './components/InputField'
import { formatDateForBackend } from './utils/dateUtils'

function App() {
  const [customers, setCustomers] = useState([]);
  
  useEffect(() => {
    fetch('/api/customers/')
      .then(response => response.json())
      .then(data => setCustomers(data))
      .catch(error => console.error('Error:', error));
  }, []);
  
  const [newCustomer, setNewCustomer] = useState({ 
    nome: '', 
    cpf: '', 
    cpf_titular: '',
    data_nascimento: '',
    endereco: '',
    telefone: '',
    email: ''
  });

  const handleAddCustomer = () => {
    if (newCustomer.nome && newCustomer.cpf && newCustomer.endereco) {
      // Prepara os dados formatando a data corretamente
      const customerData = {
        ...newCustomer,
        data_nascimento: formatDateForBackend(newCustomer.data_nascimento)
      };
      
      fetch('/api/customers/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(customerData)
      })
        .then(response => response.json())
        .then(data => {
          setCustomers([...customers, data]);
          setNewCustomer({ 
            nome: '', 
            cpf: '', 
            cpf_titular: '',
            data_nascimento: '',
            endereco: '',
            telefone: '',
            email: ''
          });
        })
        .catch(error => console.error('Error:', error));
    }
  };

  const handleDeleteCustomer = (id) => {
    fetch(`/api/customers/${id}/`, {
      method: 'DELETE'
    })
      .then(() => {
        setCustomers(customers.filter(customer => customer.id !== id));
      })
      .catch(error => console.error('Error:', error));
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="text-4xl font-bold text-indigo-600 mb-8 text-center">Cadastro de Clientes</h1>
      
      <div className="bg-white p-6 rounded-lg shadow-md max-w-6xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">Novo Cliente</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <InputField
              placeholder="Nome completo"
              value={newCustomer.nome}
              onChange={(value) => setNewCustomer({...newCustomer, nome: value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CPF do Cliente *</label>
            <InputField
              placeholder="000.000.000-00"
              value={newCustomer.cpf}
              onChange={(value) => setNewCustomer({...newCustomer, cpf: value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CPF do Titular da UC</label>
            <InputField
              placeholder="CPF do titular (se diferente)"
              value={newCustomer.cpf_titular}
              onChange={(value) => setNewCustomer({...newCustomer, cpf_titular: value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento</label>
            <input
              type="date"
              className="w-full p-2 border border-gray-300 rounded"
              value={newCustomer.data_nascimento}
              onChange={(e) => setNewCustomer({...newCustomer, data_nascimento: e.target.value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Endereço *</label>
            <InputField
              placeholder="Endereço completo"
              value={newCustomer.endereco}
              onChange={(value) => setNewCustomer({...newCustomer, endereco: value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
            <InputField
              placeholder="(00) 00000-0000"
              value={newCustomer.telefone}
              onChange={(value) => setNewCustomer({...newCustomer, telefone: value})}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
            <InputField
              placeholder="email@exemplo.com"
              value={newCustomer.email}
              onChange={(value) => setNewCustomer({...newCustomer, email: value})}
            />
          </div>
        </div>
        
        <p className="text-sm text-gray-500 mb-4">* Campos obrigatórios</p>
        
        <button 
          onClick={handleAddCustomer}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition mb-6"
        >
          Adicionar Cliente
        </button>
        
        <CustomerTable customers={customers} onDelete={handleDeleteCustomer} />
      </div>
    </div>
  )
}

export default App