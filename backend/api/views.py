# backend/api/views.py
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Customer, UnidadeConsumidora, FaturaTask, Fatura, FaturaLog
from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
import threading
import requests # Adicionado para fazer requisições HTTP
from .services.equatorial_service import EquatorialService

class CustomerSerializer(serializers.ModelSerializer):
    data_nascimento = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d/%m/%Y'])
    
    class Meta:
        model = Customer
        fields = ['id', 'nome', 'cpf', 'cpf_titular', 'data_nascimento', 
                  'endereco', 'telefone', 'email', 'created_at', 'updated_at']

class UnidadeConsumidoraSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UnidadeConsumidora
        fields = ['id', 'customer', 'codigo', 'endereco', 'tipo', 
                 'data_vigencia_inicio', 'data_vigencia_fim', 'is_active',
                 'created_at', 'updated_at']
        read_only_fields = ['is_active']

@api_view(['GET', 'POST'])
def customer_list(request):
    if request.method == 'GET':
        customers = Customer.objects.all()
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def customer_detail(request, pk):
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = CustomerSerializer(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def uc_list(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        ucs = UnidadeConsumidora.objects.filter(customer=customer)
        serializer = UnidadeConsumidoraSerializer(ucs, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['customer'] = customer_id
        serializer = UnidadeConsumidoraSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def uc_detail(request, customer_id, uc_id):
    try:
        uc = UnidadeConsumidora.objects.get(pk=uc_id, customer_id=customer_id)
    except UnidadeConsumidora.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UnidadeConsumidoraSerializer(uc)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UnidadeConsumidoraSerializer(uc, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Só permite deletar UCs inativas
        if uc.is_active:
            return Response(
                {"error": "Não é possível deletar uma UC ativa. Desative-a primeiro."},
                status=status.HTTP_400_BAD_REQUEST
            )
        uc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def uc_toggle_status(request, customer_id, uc_id):
    try:
        uc = UnidadeConsumidora.objects.get(pk=uc_id, customer_id=customer_id)
    except UnidadeConsumidora.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if uc.is_active:
        # Desativar UC
        uc.data_vigencia_fim = timezone.now().date()
    else:
        # Reativar UC
        uc.data_vigencia_fim = None
    
    uc.save()
    serializer = UnidadeConsumidoraSerializer(uc)
    return Response(serializer.data)

# Views para faturas
class FaturaSerializer(serializers.ModelSerializer):
    arquivo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Fatura
        fields = ['id', 'unidade_consumidora', 'mes_referencia', 'arquivo', 
                  'arquivo_url', 'valor', 'vencimento', 'downloaded_at']
    
    def get_arquivo_url(self, obj):
        if obj.arquivo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.arquivo.url)
        return None


class FaturaTaskSerializer(serializers.ModelSerializer):
    unidade_consumidora_codigo = serializers.CharField(source='unidade_consumidora.codigo', read_only=True)
    
    class Meta:
        model = FaturaTask
        fields = ['id', 'unidade_consumidora', 'unidade_consumidora_codigo', 
                  'status', 'created_at', 'completed_at', 'error_message']


@api_view(['POST'])
def start_fatura_import(request, customer_id):
    """
    Inicia o processo de importação de faturas.
    Esta view agora delega a tarefa de scraping para o serviço task_processor.
    Lógica aprimorada para evitar tarefas duplicadas.
    """
    try:
        customer = Customer.objects.get(pk=customer_id)
        
        # Validações de dados do cliente
        if not customer.data_nascimento:
            return Response(
                {"error": "Cliente sem data de nascimento cadastrada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cpf_titular = customer.cpf_titular or customer.cpf
        if not cpf_titular:
            return Response(
                {"error": "Cliente sem CPF cadastrado"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        active_ucs = customer.unidades_consumidoras.filter(data_vigencia_fim__isnull=True)
        if not active_ucs.exists():
            return Response(
                {"error": "Cliente não possui UCs ativas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lógica robusta para criar ou reutilizar tasks
        tasks = []
        with transaction.atomic():
            for uc in active_ucs:
                # Procura por uma tarefa existente para esta UC que possa ser reutilizada (pendente ou falha)
                task = FaturaTask.objects.filter(
                    customer=customer,
                    unidade_consumidora=uc,
                    status__in=['pending', 'failed']
                ).first()

                if task:
                    # Se encontrou, reseta o estado dela para ser executada novamente
                    task.status = 'pending'
                    task.error_message = None
                    task.completed_at = None
                    task.save()
                else:
                    # Se não encontrou nenhuma tarefa para reutilizar, cria uma nova
                    task = FaturaTask.objects.create(
                        customer=customer,
                        unidade_consumidora=uc,
                        status='pending'
                    )
                tasks.append(task)
        
        # Delega a tarefa para o Task Processor
        try:
            task_processor_url = 'http://host.docker.internal:5001/process-task'
            response = requests.post(task_processor_url, json={'customer_id': customer_id}, timeout=10)
            
            if response.status_code != 202:
                raise requests.exceptions.RequestException(f"Serviço de automação respondeu com status {response.status_code}")

        except requests.exceptions.RequestException as e:
            # Se a comunicação com o bot falhar, marca as tarefas como falhas
            error_msg = f"Não foi possível conectar ao serviço de automação: {e}"
            for task in tasks:
                task.status = 'failed'
                task.error_message = error_msg
                task.save()
            return Response(
                {"error": "Não foi possível iniciar a automação. Verifique se o 'task_processor' está ativo."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        serializer = FaturaTaskSerializer(tasks, many=True)
        return Response({
            "message": "Solicitação de importação enviada para o serviço de automação.",
            "tasks": serializer.data
        }, status=status.HTTP_202_ACCEPTED)
        
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_fatura_tasks(request, customer_id):
    """Retorna o status das tarefas de importação"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        tasks = FaturaTask.objects.filter(customer=customer).order_by('-created_at')[:10]
        serializer = FaturaTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_faturas(request, customer_id):
    """Retorna as faturas baixadas do cliente"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        faturas = Fatura.objects.filter(customer=customer).order_by('-mes_referencia')
        serializer = FaturaSerializer(faturas, many=True, context={'request': request})
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_fatura_logs(request, customer_id):
    """Retorna os logs de busca de faturas"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        logs = FaturaLog.objects.filter(customer=customer).order_by('-created_at')[:10]
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'cpf_titular': log.cpf_titular,
                'ucs_encontradas': log.ucs_encontradas,
                'faturas_encontradas': log.faturas_encontradas,
                'created_at': log.created_at
            })
        return Response(data)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)