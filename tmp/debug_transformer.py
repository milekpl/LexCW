from app.utils.lift_to_html_transformer import LIFTToHTMLTransformer, ElementConfig

lift_xml = """
<entry id="test">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
        <grammatical-info value="Noun"/>
        <definition>
            <form lang="en"><text>A procedure for testing</text></form>
        </definition>
    </sense>
    <sense>
        <grammatical-info value="Noun"/>
        <definition>
            <form lang="en"><text>An examination or trial</text></form>
        </definition>
    </sense>
</entry>
"""

configs = [
    ElementConfig(
        lift_element="grammatical-info",
        display_order=1,
        css_class="pos",
        abbr_format="full",
    )
]

transformer = LIFTToHTMLTransformer()
result = transformer.transform(lift_xml, configs, entry_level_pos="Noun")
print('RESULT:')
print(result)
print('Noun count:', result.count('Noun'))
