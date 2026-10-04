import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rhymer/rhyme_controller.dart';
import 'package:rhymer/rhyme_detector.dart';

void main() {
  testWidgets('Highlight preserves source, selection and composing range', (tester) async {
    final controller = RhymeController();
    addTearDown(controller.dispose);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: TextField(controller: controller))));
    const text = '🎵  кот\n\n\tрот!';
    controller.value = const TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: 7),
      composing: TextRange(start: 5, end: 7),
    );
    final before = controller.value;
    controller.setMarks(const [RhymeMark(4, 7, 0), RhymeMark(10, 13, 0)]);
    final span = controller.buildTextSpan(
      context: tester.element(find.byType(TextField)),
      withComposing: true,
    );
    expect(span.toPlainText(), text);
    expect(controller.value, before);
    final parts = span.children!.cast<TextSpan>();
    expect(parts.where((s) => s.style?.decoration == TextDecoration.underline)
        .map((s) => s.text).join(), 'от');
    expect(parts.where((s) => s.style?.backgroundColor != null)
        .map((s) => s.text).join(), 'кот' 'рот');
    await tester.pump();
    expect(tester.takeException(), isNull);

    controller.text = '';
    final cleared = controller.buildTextSpan(
      context: tester.element(find.byType(TextField)),
      withComposing: true,
    );
    expect(cleared.toPlainText(), isEmpty);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Composition underline can be omitted without losing highlights', (tester) async {
    final controller = RhymeController()..value = const TextEditingValue(
      text: 'кот\nрот', composing: TextRange(start: 0, end: 3),
    );
    addTearDown(controller.dispose);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: TextField(controller: controller))));
    controller.setMarks(const [RhymeMark(0, 3, 0), RhymeMark(4, 7, 0)]);
    final context = tester.element(find.byType(TextField));
    final span = controller.buildTextSpan(context: context, withComposing: false);
    expect(span.toPlainText(), controller.text);
    expect(span.children!.cast<TextSpan>().every(
      (s) => s.style?.decoration != TextDecoration.underline,
    ), isTrue);
    await tester.pumpWidget(const SizedBox());
  });
}
