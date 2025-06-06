// frontend/src/utils/dateUtils.js

export const formatDateForBackend = (dateString) => {
  if (!dateString) return '';
  
  // Cria a data no timezone local (sem conversão UTC)
  const date = new Date(dateString + 'T12:00:00');
  
  // Formata como YYYY-MM-DD
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
};

export const formatDateFromBackend = (dateString) => {
  if (!dateString) return '';
  
  // Retorna a data como está, sem conversão
  return dateString;
};