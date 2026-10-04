import 'package:flutter/material.dart';

import 'rhyme_detector.dart';

const rhymeColors = [
  Color(0xffffd54f), Color(0xff81c784), Color(0xff64b5f6), Color(0xffe57373),
  Color(0xffba68c8), Color(0xff4db6ac), Color(0xffff8a65), Color(0xffa1887f),
];

class RhymeController extends TextEditingController {
  List<RhymeMark> _marks = const [];
  String _markedText = '';

  void setMarks(List<RhymeMark> marks) {
    _marks = marks;
    _markedText = text;
    notifyListeners();
  }

  @override
  TextSpan buildTextSpan({
    required BuildContext context,
    TextStyle? style,
    required bool withComposing,
  }) {
    if (_marks.isEmpty || text != _markedText) {
      return super.buildTextSpan(context: context, style: style, withComposing: withComposing);
    }
    final composing = withComposing && value.isComposingRangeValid
        ? value.composing
        : TextRange.empty;
    final spans = <TextSpan>[];

    void append(int start, int end, Color? color) {
      if (start == end) return;
      final cuts = <int>[
        start,
        if (composing.start > start && composing.start < end) composing.start,
        if (composing.end > start && composing.end < end) composing.end,
        end,
      ];
      for (var i = 0; i < cuts.length - 1; i++) {
        final from = cuts[i], to = cuts[i + 1];
        spans.add(TextSpan(
          text: text.substring(from, to),
          style: TextStyle(
            backgroundColor: color,
            decoration: composing.start <= from && to <= composing.end
                ? TextDecoration.underline
                : null,
          ),
        ));
      }
    }

    var offset = 0;
    for (final mark in _marks) {
      append(offset, mark.start, null);
      append(mark.start, mark.end, rhymeColors[mark.group % rhymeColors.length]);
      offset = mark.end;
    }
    append(offset, text.length, null);
    return TextSpan(style: style, children: spans);
  }
}
