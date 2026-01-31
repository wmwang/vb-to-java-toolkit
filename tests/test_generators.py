"""
Java 生成器單元測試
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.generators import JavaProjectGenerator, JavaProjectConfig, ProjectType
from src.extractors import SchemaInferrer


class TestJavaProjectGenerator:
    """JavaProjectGenerator 測試"""
    
    @pytest.fixture
    def generator(self):
        """建立測試用的生成器"""
        config = JavaProjectConfig(
            group_id="com.test",
            artifact_id="test-app",
            base_package="com.test.app",
        )
        return JavaProjectGenerator(config=config)
    
    @pytest.fixture
    def schema_inferrer(self):
        """建立測試用的 Schema 推斷器"""
        inferrer = SchemaInferrer()
        
        # 手動新增測試表格
        inferrer._add_or_update_table("Customers", "test.cls")
        inferrer._add_column_to_table("Customers", "CustomerID")
        inferrer._add_column_to_table("Customers", "CustomerName")
        inferrer._add_column_to_table("Customers", "Email")
        
        # 設定主鍵
        inferrer.tables["Customers"].columns["CustomerID"].is_primary_key = True
        inferrer.tables["Customers"].columns["CustomerID"].java_type = "Long"
        inferrer.tables["Customers"].columns["CustomerName"].java_type = "String"
        inferrer.tables["Customers"].columns["Email"].java_type = "String"
        
        return inferrer
    
    @pytest.fixture
    def temp_output_dir(self):
        """建立臨時輸出目錄"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_generate_entity(self, generator, schema_inferrer):
        """測試 Entity 生成"""
        table = schema_inferrer.tables["Customers"]
        entity_file = generator._generate_entity("Customers", table)
        
        assert entity_file.layer.value == "entity"
        assert "Customers" in entity_file.content
        assert "@Entity" in entity_file.content
        assert "@Id" in entity_file.content
        assert "CustomerID" in entity_file.content or "customerId" in entity_file.content
    
    def test_generate_repository(self, generator, schema_inferrer):
        """測試 Repository 生成"""
        table = schema_inferrer.tables["Customers"]
        repo_file = generator._generate_repository("Customers", table)
        
        assert repo_file.layer.value == "repository"
        assert "CustomersRepository" in repo_file.content
        assert "JpaRepository" in repo_file.content
    
    def test_generate_usecase(self, generator, schema_inferrer):
        """測試 Use Case 生成"""
        table = schema_inferrer.tables["Customers"]
        usecase_file = generator._generate_usecase("Customers", table)
        
        assert usecase_file.layer.value == "usecase"
        assert "CustomersUseCase" in usecase_file.content
        assert "findAll" in usecase_file.content
        assert "save" in usecase_file.content
    
    def test_generate_from_schema(self, generator, schema_inferrer, temp_output_dir):
        """測試從 Schema 生成完整專案"""
        files = generator.generate_from_schema(
            schema_inferrer,
            temp_output_dir,
        )
        
        # 應該生成 Entity + Repository + UseCase = 3 個檔案
        assert len(files) == 3
        
        # 檢查檔案是否實際寫入
        output_path = Path(temp_output_dir)
        java_files = list(output_path.glob("**/*.java"))
        assert len(java_files) == 3
        
        # 檢查 pom.xml
        assert (output_path / "pom.xml").exists()
        
        # 檢查 application.properties
        assert (output_path / "src/main/resources/application.properties").exists()
    
    def test_generate_pom_xml(self, generator):
        """測試 pom.xml 生成"""
        pom = generator._generate_pom_xml()
        
        assert "com.test" in pom
        assert "test-app" in pom
        assert "spring-boot-starter" in pom
        assert "lombok" in pom
    
    def test_generate_build_gradle(self):
        """測試 build.gradle 生成"""
        config = JavaProjectConfig(project_type=ProjectType.GRADLE)
        generator = JavaProjectGenerator(config=config)
        gradle = generator._generate_build_gradle()
        
        assert "plugins" in gradle
        assert "spring-boot" in gradle
    
    def test_pascal_case_conversion(self, generator):
        """測試 PascalCase 轉換"""
        assert generator._to_pascal_case("customer_order") == "CustomerOrder"
        assert generator._to_pascal_case("user") == "User"
        assert generator._to_pascal_case("order-item") == "OrderItem"
    
    def test_camel_case_conversion(self, generator):
        """測試 camelCase 轉換"""
        assert generator._to_camel_case("customer_order") == "customerOrder"
        assert generator._to_camel_case("User") == "user"
    
    def test_get_summary(self, generator, schema_inferrer, temp_output_dir):
        """測試生成摘要"""
        generator.generate_from_schema(schema_inferrer, temp_output_dir)
        summary = generator.get_summary()
        
        assert summary["total_files"] == 3
        assert "entity" in summary["by_layer"]
        assert "repository" in summary["by_layer"]
        assert "usecase" in summary["by_layer"]


class TestJavaProjectConfig:
    """JavaProjectConfig 測試"""
    
    def test_default_config(self):
        """測試預設配置"""
        config = JavaProjectConfig()
        
        assert config.group_id == "com.example"
        assert config.artifact_id == "migrated-app"
        assert config.java_version == "17"
        assert config.use_lombok is True
        assert config.use_spring_boot is True
    
    def test_custom_config(self):
        """測試自訂配置"""
        config = JavaProjectConfig(
            group_id="com.custom",
            artifact_id="my-app",
            java_version="21",
            use_lombok=False,
        )
        
        assert config.group_id == "com.custom"
        assert config.artifact_id == "my-app"
        assert config.java_version == "21"
        assert config.use_lombok is False
