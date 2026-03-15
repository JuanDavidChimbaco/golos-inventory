from rest_framework import serializers
from ..models import FinancialCategory, CashSession, FinancialTransaction, Sale

class FinancialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialCategory
        fields = '__all__'

class FinancialTransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    created_by_name = serializers.ReadOnlyField(source='created_by')
    
    class Meta:
        model = FinancialTransaction
        fields = '__all__'
        read_only_fields = ['created_by']

class CashSessionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashSession
        fields = ['id', 'opened_at', 'opened_by', 'status', 'initial_balance', 'closed_at', 'closed_by', 'actual_balance', 'difference']

class CashSessionSerializer(serializers.ModelSerializer):
    transactions = FinancialTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = CashSession
        fields = '__all__'
