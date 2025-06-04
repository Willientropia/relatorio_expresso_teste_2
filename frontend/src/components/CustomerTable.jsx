import React from 'react';

const CustomerTable = ({ customers, onDelete }) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-6 py-3 text-left">Nome</th>
            <th className="px-6 py-3 text-left">CPF</th>
            <th className="px-6 py-3 text-left">Endereço</th>
            <th className="px-6 py-3 text-left">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {customers.map((customer) => (
            <tr key={customer.id}>
              <td className="px-6 py-4">{customer.nome}</td>
              <td className="px-6 py-4">{customer.cpf}</td>
              <td className="px-6 py-4">{customer.endereco}</td>
              <td className="px-6 py-4">
                <button 
                  onClick={() => onDelete(customer.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default CustomerTable;
