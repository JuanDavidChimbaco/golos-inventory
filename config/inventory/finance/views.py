from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q
from ..models import FinancialCategory, CashSession, FinancialTransaction
from .serializers import (
    FinancialCategorySerializer, 
    CashSessionSerializer, 
    CashSessionSimpleSerializer,
    FinancialTransactionSerializer
)

class FinancialCategoryViewSet(viewsets.ModelViewSet):
    queryset = FinancialCategory.objects.all()
    serializer_class = FinancialCategorySerializer
    filterset_fields = ['is_income', 'is_active']
    search_fields = ['name', 'description']

class FinancialTransactionViewSet(viewsets.ModelViewSet):
    queryset = FinancialTransaction.objects.all()
    serializer_class = FinancialTransactionSerializer
    filterset_fields = ['transaction_type', 'category', 'session', 'payment_method']
    search_fields = ['description', 'created_by']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.username)

class CashSessionViewSet(viewsets.ModelViewSet):
    queryset = CashSession.objects.all()
    serializer_class = CashSessionSerializer
    filterset_fields = ['status', 'opened_by']

    def get_serializer_class(self):
        if self.action == 'list':
            return CashSessionSimpleSerializer
        return CashSessionSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtiene la sesión de caja abierta actualmente"""
        session = CashSession.objects.filter(status='open').first()
        if not session:
            return Response(None, status=status.HTTP_200_OK)
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def open_session(self, request):
        """Abre una nueva sesión de caja"""
        if CashSession.objects.filter(status='open').exists():
            return Response({"detail": "Ya existe una caja abierta."}, status=status.HTTP_400_BAD_REQUEST)
        
        initial_balance = request.data.get('initial_balance', 0)
        notes = request.data.get('notes', '')
        
        session = CashSession.objects.create(
            opened_by=request.user.username,
            initial_balance=initial_balance,
            notes=notes,
            status='open'
        )
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def close_session(self, request, pk=None):
        """Cierra la sesión de caja actual"""
        session = self.get_object()
        if session.status == 'closed':
            return Response({"detail": "La caja ya está cerrada."}, status=status.HTTP_400_BAD_REQUEST)
        
        actual_balance = request.data.get('actual_balance')
        if actual_balance is None:
            return Response({"detail": "Debe proporcionar el saldo físico real."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular balance esperado
        # Ingresos - Egresos + Saldo Inicial
        totals = session.transactions.aggregate(
            incomes=Sum('amount', filter=Q(transaction_type='income')),
            expenses=Sum('amount', filter=Q(transaction_type='expense'))
        )
        
        incomes = totals['incomes'] or 0
        expenses = totals['expenses'] or 0
        expected_balance = session.initial_balance + incomes - expenses
        
        session.closed_at = timezone.now()
        session.closed_by = request.user.username
        session.expected_balance = expected_balance
        session.actual_balance = actual_balance
        session.difference = actual_balance - expected_balance
        session.status = 'closed'
        session.notes = request.data.get('notes', session.notes)
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
