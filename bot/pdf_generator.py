import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer)

from config.logger_config import logger

logger = logger.getChild("pdf_generator")


def generate_pdf_content(analysis_data, pdf_path):
    """Generate PDF report content from analysis data.

    Args:
        analysis_data (dict): Dictionary containing user analysis data
        pdf_path (str): Path where PDF should be saved
    """
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )
    font_dir = "fonts"
    pdfmetrics.registerFont(
        TTFont("DejaVuSans", os.path.join(font_dir, "DejaVuSans.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("DejaVuSans-Bold", os.path.join(font_dir, "DejaVuSans-Bold.ttf"))
    )

    # Define styles with DejaVuSans fonts
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "DejaVuSans-Bold"
    styles["Title"].fontSize = 24
    styles["Title"].spaceAfter = 30

    styles["Heading1"].fontName = "DejaVuSans-Bold"
    styles["Heading2"].fontName = "DejaVuSans-Bold"
    styles["Heading3"].fontName = "DejaVuSans-Bold"
    styles["Normal"].fontName = "DejaVuSans"
    styles["Bullet"].fontName = "DejavuSans"

    story = []

    # Title page
    story.append(Paragraph("Анализ владения английским языком", styles["Title"]))

    # Basic info
    story.append(Paragraph("Информация о пользователе:", styles["Heading1"]))
    story.append(
        Paragraph(f"Имя: {analysis_data['user_info']['name']}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Возраст: {analysis_data['user_info']['age']}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Email: {analysis_data['user_info']['email']}", styles["Normal"])
    )

    story.append(PageBreak())

    # Study Plan
    story.append(Paragraph("План обучения", styles["Title"]))
    study_plan = analysis_data["study_plan"]

    # Introduction
    story.append(Paragraph("Введение", styles["Heading1"]))
    story.append(Paragraph(study_plan["introduction"]["summary"], styles["Normal"]))

    # Key areas for improvement
    story.append(Paragraph("Ключевые области для улучшения:", styles["Heading1"]))
    for area in study_plan["introduction"]["key_areas_for_improvement"]:
        story.append(Paragraph(f"• {area}", styles["Bullet"]))

    # Detailed improvement plans
    improvement_plans = {
        "1 месяц": study_plan["detailed_improvement_plan"]["1_month_plan"],
        "3 месяца": study_plan["detailed_improvement_plan"]["3_month_plan"],
        "6 месяцев": study_plan["detailed_improvement_plan"]["6_month_plan"],
        "12 месяцев": study_plan["detailed_improvement_plan"]["12_month_plan"],
    }

    for period, plan in improvement_plans.items():
        story.append(Paragraph(f"План обучения на {period}:", styles["Heading1"]))
        story.append(Paragraph("Цели:", styles["Heading2"]))
        for goal in plan["goals"]:
            story.append(Paragraph(f"• {goal}", styles["Bullet"]))

        story.append(Paragraph("План действий:", styles["Heading2"]))
        for action in plan["action_steps"]:
            story.append(Paragraph(f"• {action}", styles["Bullet"]))
        story.append(PageBreak())

    # Action Schedule
    story.append(PageBreak())
    story.append(Paragraph("График Занятий", styles["Title"]))

    schedules = {
        "Ежедневные занятия": study_plan["action_schedule"]["daily_actions"],
        "Еженедельный план": study_plan["action_schedule"]["weekly_actions"],
        "Ежемесячный план": study_plan["action_schedule"]["monthly_actions"],
    }

    for schedule_type, activities in schedules.items():
        story.append(Paragraph(schedule_type, styles["Heading1"]))
        for activity in activities:
            story.append(Paragraph(f"• {activity}", styles["Bullet"]))

    # Resources
    story.append(PageBreak())
    story.append(Paragraph("Рекомендуемые материалы", styles["Title"]))

    for resource_type, items in study_plan["resources"].items():
        story.append(Paragraph(resource_type.capitalize(), styles["Heading1"]))
        for item in items:
            story.append(Paragraph(f"• {item}", styles["Bullet"]))

    story.append(PageBreak())

    sections = [
        (
            "Оценка словарного запаса",
            analysis_data["vocabulary"]["evaluation"],
            analysis_data["vocabulary"]["feedback"],
        ),
        (
            "Анализ грамматики",
            analysis_data["grammar"]["evaluation"],
            analysis_data["grammar"]["feedback"],
        ),
        (
            "Оценка стиля речи",
            analysis_data["style"]["evaluation"],
            analysis_data["style"]["feedback"],
        ),
        (
            "Анализ использования времен",
            analysis_data["tense"]["evaluation"],
            analysis_data["tense"]["feedback"],
        ),
        (
            "Оценка разговорных навыков",
            analysis_data["audio"]["evaluation"],
            analysis_data["audio"]["feedback"],
        ),
    ]
    logger.debug(f"Sections: {sections}")
    for title, evaluation, feedback in sections:
        add_analysis_section(story, title, evaluation, feedback, styles)

    doc.build(story)


def add_analysis_section(story, title, evaluation, feedback, styles):
    """Adds a section of analysis to the PDF report.

    Args:
        story: The PDF story object to append content to
        title: Section title
        evaluation: Dictionary containing evaluation scores and details
        feedback: Dictionary containing detailed feedback sections
        styles: Dictionary of PDF styles
    """
    story.append(Paragraph(title, styles["Heading2"]))
    story.append(Spacer(1, 12))

    # Add evaluation scores
    for criteria, details in evaluation.items():
        if criteria != "overall":
            story.append(
                Paragraph(f"{criteria.replace('_', ' ').title()}", styles["Heading3"])
            )
            story.append(Paragraph(f"Оценка: {details['score']}/10", styles["Normal"]))
            story.append(
                Paragraph(f"Анализ: {details['justification']}", styles["Normal"])
            )
            story.append(Spacer(1, 12))

    # Add overall evaluation
    if "overall" in evaluation:
        overall = evaluation["overall"]
        story.append(Paragraph("Общая оценка", styles["Heading3"]))
        story.append(Paragraph(f"Общий балл: {overall['score']}/10", styles["Normal"]))
        story.append(Spacer(1, 8))

        if overall["strengths"]:
            story.append(Paragraph("Сильные стороны:", styles["Heading4"]))
            bullet_list = ListFlowable(
                [
                    ListItem(Paragraph(item, styles["Normal"]))
                    for item in overall["strengths"]
                ],
                bulletType="bullet",
                leftIndent=20,
                spaceBefore=6,
                spaceAfter=6,
            )
            story.append(bullet_list)
            story.append(Spacer(1, 8))

        if overall["areas_for_improvement"]:
            story.append(Paragraph("Области для улучшения:", styles["Heading4"]))
            bullet_list = ListFlowable(
                [
                    ListItem(Paragraph(item, styles["Normal"]))
                    for item in overall["areas_for_improvement"]
                ],
                bulletType="bullet",
                leftIndent=20,
                spaceBefore=6,
                spaceAfter=6,
            )
            story.append(bullet_list)
            story.append(Spacer(1, 8))

        if overall["summary"]:
            story.append(Paragraph("Итог:", styles["Heading4"]))
            story.append(Paragraph(overall["summary"], styles["Normal"]))
            story.append(Spacer(1, 12))

    # Add feedback sections with improved spacing
    story.append(Paragraph(f"Детальный анализ {title.lower()}", styles["Heading3"]))
    story.append(Spacer(1, 8))

    sections = [
        ("Примеры сильных сторон:", "Specific examples that demonstrate strong skills"),
        ("Области для улучшения:", "Areas where improvement is needed"),
        ("Рекомендуемые упражнения:", "Suggested exercises or practice activities"),
        ("Общие рекомендации:", "General recommendations for further development"),
    ]

    for section_title, section_key in sections:
        story.append(Paragraph(section_title, styles["Heading4"]))
        bullet_list = ListFlowable(
            [
                ListItem(Paragraph(item, styles["Normal"]))
                for item in feedback[section_key]
            ],
            bulletType="bullet",
            leftIndent=20,
            spaceBefore=6,
            spaceAfter=6,
        )
        story.append(bullet_list)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 20))