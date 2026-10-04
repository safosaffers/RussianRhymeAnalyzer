import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'rhyme_controller.dart';
import 'rhyme_detector.dart';

void main() => runApp(const RhymerApp());

class RhymerApp extends StatelessWidget {
  const RhymerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'rhymer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff52694d)),
        scaffoldBackgroundColor: const Color(0xfffaf9f5),
      ),
      home: const RhymeEditor(),
    );
  }
}

class RhymeEditor extends StatefulWidget {
  const RhymeEditor({super.key});

  @override
  State<RhymeEditor> createState() => _RhymeEditorState();
}

class _RhymeEditorState extends State<RhymeEditor> {
  final _controller = RhymeController();
  Timer? _debounce;
  String _lastText = '';
  bool _analyzing = false;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onEdit);
  }

  void _onEdit() {
    if (_controller.text == _lastText) return;
    _lastText = _controller.text;
    _controller.setMarks(const []);
    if (_failed) setState(() => _failed = false);
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 180), _analyze);
  }

  Future<void> _analyze() async {
    if (_analyzing || _controller.text.isEmpty) return;
    final text = _controller.text;
    _analyzing = true;
    try {
      final marks = await compute(detectRhymes, text);
      if (mounted && _controller.text == text) _controller.setMarks(marks);
    } catch (error, stack) {
      debugPrint('Rhyme analysis failed: $error\n$stack');
      if (mounted && _controller.text == text) setState(() => _failed = true);
    } finally {
      _analyzing = false;
      // Пока идёт расчёт, правки объединяются в один следующий запуск.
      if (mounted && _controller.text != text) {
        _debounce?.cancel();
        _debounce = Timer(const Duration(milliseconds: 180), _analyze);
      }
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.removeListener(_onEdit);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('rhymer'),
        backgroundColor: Colors.transparent,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: TextField(
            controller: _controller,
            expands: true,
            minLines: null,
            maxLines: null,
            textAlignVertical: TextAlignVertical.top,
            keyboardType: TextInputType.multiline,
            textCapitalization: TextCapitalization.sentences,
            style: const TextStyle(fontSize: 20, height: 1.65, color: Color(0xff252923)),
            decoration: InputDecoration(
              hintText: 'Пиши стихи здесь.\nРифмы подсветятся сами.',
              errorText: _failed ? 'Не удалось подсветить рифмы. Попробуй изменить текст.' : null,
              filled: true,
              fillColor: Colors.white,
              contentPadding: const EdgeInsets.all(20),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
            ),
          ),
        ),
      ),
    );
  }
}
