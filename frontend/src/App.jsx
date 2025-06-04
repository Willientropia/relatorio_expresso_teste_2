import { useState, useEffect } from 'react'
import CustomerTable from './components/CustomerTable'
import InputField from './components/InputField'

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
    endereco: '' 
  });

  const handleAddCustomer = () => {
    if (newCustomer.nome && newCustomer.cpf && newCustomer.endereco) {
      fetch('/api/customers/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newCustomer)
      })
        .then(response => response.json())
        .then(data => {
          setCustomers([...customers, data]);
          setNewCustomer({ nome: '', cpf: '', endereco: '' });
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
      
      <div className="bg-white p-6 rounded-lg shadow-md max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <InputField
            placeholder="Nome"
            value={newCustomer.nome}
            onChange={(value) => setNewCustomer({...newCustomer, nome: value})}
          />
          <InputField
            placeholder="CPF"
            value={newCustomer.cpf}
            onChange={(value) => setNewCustomer({...newCustomer, cpf: value})}
          />
          <InputField
            placeholder="Endereço"
            value={newCustomer.endereco}
            onChange={(value) => setNewCustomer({...newCustomer, endereco: value})}
          />
        </div>
        
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
