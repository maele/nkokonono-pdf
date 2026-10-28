from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class HtmlToPdfProcessor(BaseProcessor):
    tool_name = "html-to-pdf"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "HTML to PDF accepts exactly one HTML file.")
        try:
            import weasyprint  # noqa: F401
        except ImportError:
            raise ProcessorError("CONVERSION_FAILED", "WeasyPrint is not installed.")

    def process(self, inputs, options, output_dir):
        from weasyprint import HTML

        out = output_dir / "rendered.pdf"
        try:
            # filename= form: WeasyPrint resolves relative asset paths against
            # the HTML file's own directory, and by default does not fetch
            # remote URLs. That is the safety boundary for this tool.
            HTML(filename=str(inputs[0].storage_path)).write_pdf(str(out))
        except Exception as exc:
            raise ProcessorError("CONVERSION_FAILED", f"HTML rendering failed: {exc}")
        if not out.exists():
            raise ProcessorError("OUTPUT_VALIDATION_FAILED", "No PDF was produced.")
        return [ProcessorOutput(path=out, display_name="rendered.pdf", mime_type="application/pdf")]