"""
Java 專案生成器 - 生成完整的 Java Clean Architecture 專案結構

功能：
1. 生成 Entity 層程式碼
2. 生成 Use Case 層程式碼
3. 生成 Repository Interface
4. 生成 Controller 層程式碼
5. 輸出標準 Maven 專案結構
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from pathlib import Path
from enum import Enum
import os

from ..extractors.schema_inferrer import SchemaInferrer, InferredTable
from ..llm.java_translator import JavaCodeTranslator, JavaLayer, TranslationResult


class ProjectType(Enum):
    """專案類型"""
    MAVEN = "maven"
    GRADLE = "gradle"


@dataclass
class GeneratedFile:
    """生成的檔案"""
    relative_path: str
    content: str
    layer: JavaLayer
    source_name: str  # 原始 VB 類別/函數名稱


@dataclass
class JavaProjectConfig:
    """Java 專案配置"""
    group_id: str = "com.example"
    artifact_id: str = "migrated-app"
    version: str = "1.0.0"
    base_package: str = "com.example.app"
    java_version: str = "17"
    project_type: ProjectType = ProjectType.MAVEN
    use_lombok: bool = True
    use_spring_boot: bool = True


class JavaProjectGenerator:
    """Java 專案生成器"""
    
    def __init__(
        self,
        config: Optional[JavaProjectConfig] = None,
        translator: Optional[JavaCodeTranslator] = None,
    ):
        """
        初始化生成器
        
        Args:
            config: Java 專案配置
            translator: Java 轉譯器（用於 LLM 輔助生成）
        """
        self.config = config or JavaProjectConfig()
        self.translator = translator
        self.generated_files: List[GeneratedFile] = []
    
    def generate_from_schema(
        self,
        schema_inferrer: SchemaInferrer,
        output_dir: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> List[GeneratedFile]:
        """
        從 Schema 推斷結果生成 Java 專案
        
        Args:
            schema_inferrer: Schema 推斷器實例
            output_dir: 輸出目錄
            on_progress: 進度回調 (message, current, total)
            
        Returns:
            生成的檔案列表
        """
        tables = schema_inferrer.tables
        total = len(tables) * 3  # Entity + Repository + UseCase
        current = 0
        
        for table_name, table in tables.items():
            # 生成 Entity
            if on_progress:
                on_progress(f"生成 Entity: {table_name}", current, total)
            entity_file = self._generate_entity(table_name, table)
            self.generated_files.append(entity_file)
            current += 1
            
            # 生成 Repository
            if on_progress:
                on_progress(f"生成 Repository: {table_name}", current, total)
            repo_file = self._generate_repository(table_name, table)
            self.generated_files.append(repo_file)
            current += 1
            
            # 生成 Use Case (基本 CRUD)
            if on_progress:
                on_progress(f"生成 UseCase: {table_name}", current, total)
            usecase_file = self._generate_usecase(table_name, table)
            self.generated_files.append(usecase_file)
            current += 1
        
        # 寫入檔案
        self._write_files(output_dir)
        
        # 生成專案配置檔
        self._generate_project_files(output_dir)
        
        return self.generated_files
    
    def _generate_entity(self, table_name: str, table: InferredTable) -> GeneratedFile:
        """生成 Entity 類別"""
        class_name = self._to_pascal_case(table_name)
        package = f"{self.config.base_package}.domain.entity"
        
        lines = [
            f"package {package};",
            "",
        ]
        
        # Imports
        imports = [
            "import jakarta.persistence.*;",
        ]
        if self.config.use_lombok:
            imports.extend([
                "import lombok.Data;",
                "import lombok.NoArgsConstructor;",
                "import lombok.AllArgsConstructor;",
            ])
        
        # 檢查是否需要 LocalDateTime
        needs_datetime = any(
            col.java_type == "LocalDateTime" 
            for col in table.columns.values()
        )
        if needs_datetime:
            imports.append("import java.time.LocalDateTime;")
        
        lines.extend(imports)
        lines.append("")
        
        # 類別定義
        lines.append("/**")
        lines.append(f" * {class_name} Entity")
        lines.append(f" * 來源表格：{table_name}")
        lines.append(" */")
        
        if self.config.use_lombok:
            lines.append("@Data")
            lines.append("@NoArgsConstructor")
            lines.append("@AllArgsConstructor")
        
        lines.append("@Entity")
        lines.append(f"@Table(name = \"{table_name}\")")
        lines.append(f"public class {class_name} {{")
        lines.append("")
        
        # 欄位
        for col_name, col in table.columns.items():
            field_name = self._to_camel_case(col_name)
            java_type = col.java_type
            
            # JPA 註解
            if col.is_primary_key:
                lines.append("    @Id")
                lines.append("    @GeneratedValue(strategy = GenerationType.IDENTITY)")
            
            if col.is_foreign_key and col.references_table:
                ref_class = self._to_pascal_case(col.references_table)
                lines.append(f"    @ManyToOne(fetch = FetchType.LAZY)")
                lines.append(f"    @JoinColumn(name = \"{col_name}\")")
                lines.append(f"    private {ref_class} {self._to_camel_case(col.references_table)};")
            else:
                lines.append(f"    @Column(name = \"{col_name}\")")
                lines.append(f"    private {java_type} {field_name};")
            
            lines.append("")
        
        # 如果不使用 Lombok，生成 getters/setters
        if not self.config.use_lombok:
            lines.extend(self._generate_getters_setters(table))
        
        lines.append("}")
        
        relative_path = self._get_java_file_path(package, class_name)
        return GeneratedFile(
            relative_path=relative_path,
            content="\n".join(lines),
            layer=JavaLayer.ENTITY,
            source_name=table_name,
        )
    
    def _generate_repository(self, table_name: str, table: InferredTable) -> GeneratedFile:
        """生成 Repository Interface"""
        class_name = self._to_pascal_case(table_name)
        entity_name = class_name
        repo_name = f"{class_name}Repository"
        package = f"{self.config.base_package}.domain.repository"
        
        # 找出主鍵類型
        pk_type = "Long"
        for col in table.columns.values():
            if col.is_primary_key:
                pk_type = col.java_type
                break
        
        lines = [
            f"package {package};",
            "",
            "import org.springframework.data.jpa.repository.JpaRepository;",
            "import org.springframework.stereotype.Repository;",
            f"import {self.config.base_package}.domain.entity.{entity_name};",
            "",
            "/**",
            f" * {entity_name} Repository",
            " */",
            "@Repository",
            f"public interface {repo_name} extends JpaRepository<{entity_name}, {pk_type}> {{",
            "",
            "    // 可在此新增自定義查詢方法",
            "",
            "}",
        ]
        
        relative_path = self._get_java_file_path(package, repo_name)
        return GeneratedFile(
            relative_path=relative_path,
            content="\n".join(lines),
            layer=JavaLayer.REPOSITORY,
            source_name=table_name,
        )
    
    def _generate_usecase(self, table_name: str, table: InferredTable) -> GeneratedFile:
        """生成 Use Case 類別（基本 CRUD）"""
        class_name = self._to_pascal_case(table_name)
        entity_name = class_name
        usecase_name = f"{class_name}UseCase"
        repo_name = f"{class_name}Repository"
        package = f"{self.config.base_package}.application.usecase"
        
        # 找出主鍵類型
        pk_type = "Long"
        for col in table.columns.values():
            if col.is_primary_key:
                pk_type = col.java_type
                break
        
        lines = [
            f"package {package};",
            "",
            "import org.springframework.stereotype.Service;",
            "import org.springframework.transaction.annotation.Transactional;",
            f"import {self.config.base_package}.domain.entity.{entity_name};",
            f"import {self.config.base_package}.domain.repository.{repo_name};",
            "import java.util.List;",
            "import java.util.Optional;",
        ]
        
        if self.config.use_lombok:
            lines.append("import lombok.RequiredArgsConstructor;")
        
        lines.extend([
            "",
            "/**",
            f" * {entity_name} Use Case",
            f" * 來源：{table_name}",
            " */",
            "@Service",
            "@Transactional",
        ])
        
        if self.config.use_lombok:
            lines.append("@RequiredArgsConstructor")
        
        lines.append(f"public class {usecase_name} {{")
        lines.append("")
        lines.append(f"    private final {repo_name} repository;")
        lines.append("")
        
        # 如果不使用 Lombok，生成建構子
        if not self.config.use_lombok:
            lines.extend([
                f"    public {usecase_name}({repo_name} repository) {{",
                "        this.repository = repository;",
                "    }",
                "",
            ])
        
        # CRUD 方法
        var_name = self._to_camel_case(class_name)
        
        lines.extend([
            "    /**",
            f"     * 取得所有 {entity_name}",
            "     */",
            f"    public List<{entity_name}> findAll() {{",
            "        return repository.findAll();",
            "    }",
            "",
            "    /**",
            f"     * 根據 ID 取得 {entity_name}",
            "     */",
            f"    public Optional<{entity_name}> findById({pk_type} id) {{",
            "        return repository.findById(id);",
            "    }",
            "",
            "    /**",
            f"     * 儲存 {entity_name}",
            "     */",
            f"    public {entity_name} save({entity_name} {var_name}) {{",
            f"        return repository.save({var_name});",
            "    }",
            "",
            "    /**",
            f"     * 刪除 {entity_name}",
            "     */",
            f"    public void deleteById({pk_type} id) {{",
            "        repository.deleteById(id);",
            "    }",
            "",
            "}",
        ])
        
        relative_path = self._get_java_file_path(package, usecase_name)
        return GeneratedFile(
            relative_path=relative_path,
            content="\n".join(lines),
            layer=JavaLayer.USE_CASE,
            source_name=table_name,
        )
    
    async def generate_from_vb_functions(
        self,
        vb_functions: List[Dict],
        output_dir: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> List[GeneratedFile]:
        """
        使用 LLM 從 VB 函數生成 Java 程式碼
        
        Args:
            vb_functions: VB 函數列表，每個元素包含 name, body, context
            output_dir: 輸出目錄
            on_progress: 進度回調
            on_chunk: LLM streaming 回調
            
        Returns:
            生成的檔案列表
        """
        if not self.translator:
            raise ValueError("需要提供 JavaCodeTranslator 實例才能使用 LLM 轉譯功能")
        
        total = len(vb_functions)
        
        for i, func in enumerate(vb_functions):
            func_name = func.get("name", f"Function{i}")
            func_body = func.get("body", "")
            context = func.get("context", None)
            target_layer = func.get("layer", JavaLayer.USE_CASE)
            
            if on_progress:
                on_progress(f"轉譯 {func_name}", i, total)
            
            result = await self.translator.translate_function(
                vb_code=func_body,
                function_name=func_name,
                target_layer=target_layer,
                context=context,
                on_chunk=on_chunk,
            )
            
            # 轉換為 GeneratedFile
            package = self._get_package_for_layer(target_layer)
            relative_path = self._get_java_file_path(package, result.class_name)
            
            generated_file = GeneratedFile(
                relative_path=relative_path,
                content=result.java_code,
                layer=target_layer,
                source_name=func_name,
            )
            self.generated_files.append(generated_file)
        
        # 寫入檔案
        self._write_files(output_dir)
        
        return self.generated_files
    
    def _get_package_for_layer(self, layer: JavaLayer) -> str:
        """取得層級對應的 package"""
        mapping = {
            JavaLayer.ENTITY: f"{self.config.base_package}.domain.entity",
            JavaLayer.USE_CASE: f"{self.config.base_package}.application.usecase",
            JavaLayer.REPOSITORY: f"{self.config.base_package}.domain.repository",
            JavaLayer.CONTROLLER: f"{self.config.base_package}.adapter.controller",
            JavaLayer.DTO: f"{self.config.base_package}.adapter.dto",
        }
        return mapping.get(layer, self.config.base_package)
    
    def _get_java_file_path(self, package: str, class_name: str) -> str:
        """取得 Java 檔案的相對路徑"""
        package_path = package.replace(".", "/")
        return f"src/main/java/{package_path}/{class_name}.java"
    
    def _write_files(self, output_dir: str):
        """將生成的檔案寫入磁碟"""
        output_path = Path(output_dir)
        
        for file in self.generated_files:
            file_path = output_path / file.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding="utf-8")
    
    def _generate_project_files(self, output_dir: str):
        """生成專案配置檔（pom.xml 或 build.gradle）"""
        output_path = Path(output_dir)
        
        if self.config.project_type == ProjectType.MAVEN:
            pom_content = self._generate_pom_xml()
            (output_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        else:
            gradle_content = self._generate_build_gradle()
            (output_path / "build.gradle").write_text(gradle_content, encoding="utf-8")
        
        # 生成 application.properties
        props_content = self._generate_application_properties()
        props_path = output_path / "src/main/resources/application.properties"
        props_path.parent.mkdir(parents=True, exist_ok=True)
        props_path.write_text(props_content, encoding="utf-8")
    
    def _generate_pom_xml(self) -> str:
        """生成 Maven pom.xml"""
        lombok_dep = ""
        if self.config.use_lombok:
            lombok_dep = """
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>"""
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>
    </parent>
    
    <groupId>{self.config.group_id}</groupId>
    <artifactId>{self.config.artifact_id}</artifactId>
    <version>{self.config.version}</version>
    <packaging>jar</packaging>
    
    <properties>
        <java.version>{self.config.java_version}</java.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>{lombok_dep}
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""
    
    def _generate_build_gradle(self) -> str:
        """生成 Gradle build.gradle"""
        lombok_line = ""
        if self.config.use_lombok:
            lombok_line = """
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'"""
        
        return f"""plugins {{
    id 'java'
    id 'org.springframework.boot' version '3.2.0'
    id 'io.spring.dependency-management' version '1.1.4'
}}

group = '{self.config.group_id}'
version = '{self.config.version}'

java {{
    sourceCompatibility = '{self.config.java_version}'
}}

repositories {{
    mavenCentral()
}}

dependencies {{
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    runtimeOnly 'com.h2database:h2'{lombok_line}
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}}

tasks.named('test') {{
    useJUnitPlatform()
}}
"""
    
    def _generate_application_properties(self) -> str:
        """生成 application.properties"""
        return """# 資料庫設定（開發用 H2）
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA 設定
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=true

# H2 Console（僅開發用）
spring.h2.console.enabled=true
spring.h2.console.path=/h2-console
"""
    
    def _generate_getters_setters(self, table: InferredTable) -> List[str]:
        """生成 Getters 和 Setters（當不使用 Lombok 時）"""
        lines = []
        
        for col_name, col in table.columns.items():
            field_name = self._to_camel_case(col_name)
            java_type = col.java_type
            pascal_name = self._to_pascal_case(col_name)
            
            # Getter
            lines.append(f"    public {java_type} get{pascal_name}() {{")
            lines.append(f"        return {field_name};")
            lines.append("    }")
            lines.append("")
            
            # Setter
            lines.append(f"    public void set{pascal_name}({java_type} {field_name}) {{")
            lines.append(f"        this.{field_name} = {field_name};")
            lines.append("    }")
            lines.append("")
        
        return lines
    
    def _to_pascal_case(self, name: str) -> str:
        """轉換為 PascalCase"""
        words = name.replace("_", " ").replace("-", " ").split()
        return "".join(word.capitalize() for word in words)
    
    def _to_camel_case(self, name: str) -> str:
        """轉換為 camelCase"""
        pascal = self._to_pascal_case(name)
        return pascal[0].lower() + pascal[1:] if pascal else ""
    
    def get_summary(self) -> Dict:
        """取得生成摘要"""
        summary = {
            "total_files": len(self.generated_files),
            "by_layer": {},
        }
        
        for file in self.generated_files:
            layer_name = file.layer.value
            if layer_name not in summary["by_layer"]:
                summary["by_layer"][layer_name] = []
            summary["by_layer"][layer_name].append(file.relative_path)
        
        return summary
