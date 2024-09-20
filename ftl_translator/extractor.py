from __future__ import annotations

from fluent.syntax import parse, ast
from typing import List, Tuple
from dataclasses import dataclass, field


# Датакласс для хранения информации о сообщениях
@dataclass
class MessageInfo:
    name: str  # Название переменной сообщения
    text: str  # Текст сообщения с замененными переменными
    variables: List[str]  # Список пользовательских переменных, использованных в сообщении
    term_variables: List[str]  # Список системных переменных (терминов)
    original_text: str = ""  # Оригинальный текст сообщения до замены
    all_variables: List[str] = field(
        default_factory=list
    )  # Полный список переменных для замены индексов

    @classmethod
    def get_message_info(cls, resource: ast.Resource) -> List[MessageInfo]:
        return get_message_info(resource)

    def restore_text_with_variables(self) -> str:
        """Восстанавливает текст сообщения, заменяя индексы переменных на их оригинальные значения."""
        restored_text = self.text
        for i, var_name in enumerate(self.all_variables):
            if not var_name.startswith("-"):
                var_name = f"${var_name}"
            restored_text = restored_text.replace(f"{{{i}}}", f"{{ {var_name} }}")

        return restored_text

    def to_fluent(self) -> str:
        """Восстанавливает оригинальный формат .ftl сообщения."""
        restored = self.restore_text_with_variables()
        # ставим 4 пробела перед каждой новой строкой
        fluent_text = f"{self.name} =\n    {restored.replace('\n', '\n    ')}"
        return fluent_text


# Функция для замены переменных на индексы в шаблоне текста
def replace_variables_with_indexes(pattern: ast.Pattern) -> Tuple[str, List[str], List[str], str]:
    text = ""
    user_variables = []
    term_variables = []
    all_variables = []  # Список для хранения всех переменных с индексами
    index = 0
    original_text = ""

    for element in pattern.elements:
        if isinstance(element, ast.TextElement):
            text += element.value
            original_text += element.value
        elif isinstance(element, ast.Placeable):
            # Получаем текст для Placeable и обновляем индексы
            placeable_text, placeable_original, placeable_variables, placeable_terms = (
                process_placeable(element, index)
            )
            # Используем полное значение вместо индекса для сложных выражений
            text += placeable_text
            original_text += placeable_original
            user_variables.extend(placeable_variables)
            term_variables.extend(placeable_terms)
            all_variables.extend(placeable_variables + placeable_terms)
            index += 1

    return text, user_variables, term_variables, original_text


# Функция для обработки Placeable
def process_placeable(
    placeable: ast.Placeable, index: int
) -> Tuple[str, str, List[str], List[str]]:
    expression = placeable.expression
    variables = []
    term_variables = []
    text = ""
    original_text = ""

    if isinstance(expression, ast.VariableReference):
        var_name = expression.id.name
        variables.append(var_name)
        text = f"{{{index}}}"
        original_text = f"{{ ${var_name} }}"
    elif isinstance(expression, ast.TermReference):
        term_name = expression.id.name
        term_variables.append(term_name)
        text = f"{{{index}}}"
        original_text = f"{{ -{term_name} }}"
    elif isinstance(expression, ast.MessageReference):
        message_name = expression.id.name
        variables.append(message_name)
        text = f"{{{index}}}"
        original_text = f"{{ ${message_name} }}"
    elif isinstance(expression, ast.SelectExpression):
        # Обработка SelectExpression
        select_text, select_variables, select_terms, select_original_text = (
            process_select_expression(expression)
        )
        variables.extend(select_variables)
        term_variables.extend(select_terms)
        text = select_text
        original_text = select_original_text
    elif isinstance(expression, ast.StringLiteral):
        original_text = f'"{expression.value}"'
        text = original_text
    elif isinstance(expression, ast.NumberLiteral):
        original_text = f"{expression.value}"
        text = original_text

    return text, original_text, variables, term_variables


# Функция для обработки SelectExpression
def process_select_expression(
    expression: ast.SelectExpression,
) -> Tuple[str, List[str], List[str], str]:
    variables = []
    term_variables = []
    original_text = f"{{ {expression.selector.id.name} ->\n"

    if isinstance(expression.selector, ast.VariableReference):
        variables.append(expression.selector.id.name)
    elif isinstance(expression.selector, (ast.MessageReference, ast.TermReference)):
        term_variables.append(expression.selector.id.name)

    # Обработка вариантов в SelectExpression
    for variant in expression.variants:
        if isinstance(variant.value, ast.Pattern):
            variant_text, variant_variables, variant_terms, variant_original_text = (
                replace_variables_with_indexes(variant.value)
            )
            variables.extend(variant_variables)
            term_variables.extend(variant_terms)
            original_text += f"   [{variant.key.name}] {variant_original_text}\n"

    original_text += "}"
    return original_text, variables, term_variables, original_text


# Функция для получения информации о сообщениях
def get_message_info(resource: ast.Resource) -> List[MessageInfo]:
    messages_info = []

    for entry in resource.body:
        if isinstance(entry, ast.Message):
            # Название сообщения
            message_id = entry.id.name

            # Основной текст сообщения с заменой переменных
            message_text = ""
            user_variables = []
            term_variables = []
            original_text = ""
            all_variables = []

            if entry.value:
                message_text, user_variables, term_variables, original_text = (
                    replace_variables_with_indexes(entry.value)
                )
                term_variables = [f"-{term}" for term in term_variables]
                all_variables = user_variables + term_variables

            # Обработка атрибутов (если необходимо)
            for attribute in entry.attributes:
                attr_text, attr_user_vars, attr_term_vars, attr_original_text = (
                    replace_variables_with_indexes(attribute.value)
                )
                message_text += f"\n.{attribute.id.name} = {attr_text}"
                original_text += f"\n.{attribute.id.name} = {attr_original_text}"
                user_variables.extend(attr_user_vars)
                term_variables.extend(attr_term_vars)
                all_variables.extend(attr_user_vars + attr_term_vars)

            messages_info.append(
                MessageInfo(
                    name=message_id,
                    text=message_text,
                    variables=user_variables,
                    term_variables=term_variables,
                    original_text=original_text,
                    all_variables=all_variables,
                )
            )

    return messages_info
