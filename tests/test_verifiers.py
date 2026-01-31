"""
行為驗證器單元測試
"""

import pytest
from src.verifiers import (
    BehaviorVerifier,
    VerificationResult,
    VerificationStatus,
    TestCase,
)
from src.extractors.business_logic_extractor import (
    BusinessRule,
    BusinessRuleType,
    DecisionCondition,
)


class TestBehaviorVerifier:
    """BehaviorVerifier 測試"""
    
    @pytest.fixture
    def verifier(self):
        """建立測試用的驗證器"""
        return BehaviorVerifier()
    
    @pytest.fixture
    def sample_decision_rule(self):
        """建立測試用的決策規則"""
        return BusinessRule(
            name="CalculateDiscount",
            rule_type=BusinessRuleType.DECISION,
            description="計算會員折扣",
            source_function="CalculateDiscount",
            source_file="Customer.cls",
            decision_table=[
                DecisionCondition(
                    condition="MemberLevel >= 3",
                    result="Discount = 0.2",
                    line_number=10,
                ),
                DecisionCondition(
                    condition="MemberLevel >= 1",
                    result="Discount = 0.1",
                    line_number=12,
                ),
                DecisionCondition(
                    condition="Else",
                    result="Discount = 0",
                    line_number=14,
                ),
            ],
            input_variables=["MemberLevel", "TotalAmount"],
            output_variable="Discount",
        )
    
    @pytest.fixture
    def sample_calculation_rule(self):
        """建立測試用的計算規則"""
        return BusinessRule(
            name="CalculateTax",
            rule_type=BusinessRuleType.CALCULATION,
            description="計算稅金",
            source_function="CalculateTax",
            formula="Tax = Amount * TaxRate",
            input_variables=["Amount", "TaxRate"],
            output_variable="Tax",
        )
    
    @pytest.fixture
    def sample_validation_rule(self):
        """建立測試用的驗證規則"""
        return BusinessRule(
            name="ValidateEmail",
            rule_type=BusinessRuleType.VALIDATION,
            description="驗證 Email 格式",
            source_function="ValidateEmail",
            input_variables=["Email"],
        )
    
    def test_generate_decision_test_cases(self, verifier, sample_decision_rule):
        """測試從決策規則生成測試案例"""
        cases = verifier._generate_decision_test_cases(sample_decision_rule)
        
        # 3 個條件 + 可能的邊界案例
        assert len(cases) >= 3
        
        # 檢查基本案例
        assert any("MemberLevel" in str(c.inputs) for c in cases)
    
    def test_generate_calculation_test_cases(self, verifier, sample_calculation_rule):
        """測試從計算規則生成測試案例"""
        cases = verifier._generate_calculation_test_cases(sample_calculation_rule)
        
        # 基本 + 零值 + 負值 = 3 個案例
        assert len(cases) == 3
        
        # 檢查邊界案例
        boundary_cases = [c for c in cases if c.is_boundary_case]
        assert len(boundary_cases) == 2
    
    def test_generate_validation_test_cases(self, verifier, sample_validation_rule):
        """測試從驗證規則生成測試案例"""
        cases = verifier._generate_validation_test_cases(sample_validation_rule)
        
        # 有效 + 無效 + 空值 = 3 個案例
        assert len(cases) == 3
        
        # 檢查包含邊界案例
        assert any(c.is_boundary_case for c in cases)
    
    def test_generate_test_cases_from_rules(
        self, verifier, sample_decision_rule, sample_calculation_rule
    ):
        """測試批量生成測試案例"""
        rules = [sample_decision_rule, sample_calculation_rule]
        cases = verifier.generate_test_cases_from_rules(rules)
        
        assert len(cases) > 0
        
        # 應包含兩個規則的案例
        rule_names = {c.source_rule for c in cases}
        assert "CalculateDiscount" in rule_names
        assert "CalculateTax" in rule_names
    
    def test_verify_consistency_no_java_code(self, verifier, sample_decision_rule):
        """測試一致性驗證 - 無對應 Java 程式碼"""
        results = verifier.verify_consistency(
            rules=[sample_decision_rule],
            java_translations={},  # 空的翻譯結果
        )
        
        assert len(results) == 1
        assert results[0].status == VerificationStatus.WARNING
        assert "找不到" in results[0].message
    
    def test_verify_consistency_with_java_code(self, verifier, sample_decision_rule):
        """測試一致性驗證 - 有對應 Java 程式碼"""
        java_code = """
        public double calculateDiscount(int memberLevel, double totalAmount) {
            if (memberLevel >= 3) {
                return 0.2;
            } else if (memberLevel >= 1) {
                return 0.1;
            }
            return 0;
        }
        """
        
        results = verifier.verify_consistency(
            rules=[sample_decision_rule],
            java_translations={"CalculateDiscount": java_code},
        )
        
        assert len(results) == 1
        # 應該通過基本檢查（包含 if 判斷）
        assert results[0].status in [VerificationStatus.PASSED, VerificationStatus.WARNING]
    
    def test_export_test_cases_junit(self, verifier, sample_decision_rule):
        """測試匯出 JUnit 測試程式碼"""
        cases = verifier._generate_decision_test_cases(sample_decision_rule)
        junit_code = verifier.export_test_cases_junit(cases, "CalculateDiscount")
        
        assert "import org.junit.jupiter.api.Test" in junit_code
        assert "class CalculateDiscountTest" in junit_code
        assert "@Test" in junit_code
    
    def test_generate_report_markdown(self, verifier, sample_decision_rule):
        """測試生成 Markdown 報告"""
        # 先執行驗證
        verifier.verify_consistency(
            rules=[sample_decision_rule],
            java_translations={},
        )
        
        report = verifier.generate_report_markdown()
        
        assert "# 行為驗證報告" in report
        assert "CalculateDiscount" in report
        assert "摘要" in report
    
    def test_parse_condition_inputs(self, verifier):
        """測試條件解析"""
        inputs = verifier._parse_condition_inputs("x > 10")
        assert "x" in inputs
        
        inputs = verifier._parse_condition_inputs("name = 'test'")
        assert "name" in inputs
    
    def test_to_camel_case(self, verifier):
        """測試 camelCase 轉換"""
        assert verifier._to_camel_case("member_level") == "memberLevel"
        assert verifier._to_camel_case("total-amount") == "totalAmount"


class TestTestCase:
    """TestCase 測試"""
    
    def test_to_dict(self):
        """測試序列化"""
        tc = TestCase(
            name="TestCase1",
            description="測試說明",
            inputs={"x": 10},
            expected_output="result",
            source_rule="Rule1",
            is_boundary_case=True,
        )
        
        data = tc.to_dict()
        
        assert data["name"] == "TestCase1"
        assert data["inputs"] == {"x": 10}
        assert data["is_boundary_case"] is True


class TestVerificationResult:
    """VerificationResult 測試"""
    
    def test_to_dict(self):
        """測試序列化"""
        result = VerificationResult(
            rule_name="TestRule",
            status=VerificationStatus.PASSED,
            message="驗證通過",
            java_code_issues=["Issue1"],
            suggestions=["Suggestion1"],
        )
        
        data = result.to_dict()
        
        assert data["rule_name"] == "TestRule"
        assert data["status"] == "passed"
        assert len(data["java_code_issues"]) == 1
