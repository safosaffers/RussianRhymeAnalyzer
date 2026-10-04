import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rhymer/main.dart';

void main() {
  testWidgets('One editor highlights typed rhymes and clears deleted text', (tester) async {
    await tester.pumpWidget(const RhymerApp());
    expect(find.byType(TextField), findsOneWidget);
    final field = find.byType(TextField);
    final controller = tester.widget<TextField>(field).controller!;
    await tester.enterText(field, 'кот\nрот');
    await tester.pump(const Duration(milliseconds: 200));

    bool highlighted() => controller.buildTextSpan(
      context: tester.element(field), withComposing: true,
    ).children?.cast<TextSpan>().any((s) => s.style?.backgroundColor != null) ?? false;

    for (var i = 0; i < 100 && !highlighted(); i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 20)));
      await tester.pump();
    }
    expect(highlighted(), isTrue);
    expect(controller.text, 'кот\nрот');
    await tester.enterText(field, '');
    await tester.pump(const Duration(milliseconds: 200));
    expect(highlighted(), isFalse);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Leaving editor cancels pending analysis', (tester) async {
    await tester.pumpWidget(const RhymerApp());
    await tester.enterText(find.byType(TextField), 'кот\nрот');
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
    expect(tester.takeException(), isNull);
  });
}
