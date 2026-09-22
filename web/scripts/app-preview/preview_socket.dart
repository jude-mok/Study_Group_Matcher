import 'dart:async';
import 'dart:convert';
import 'preview_data.dart';
class WebSocket {
  final String room;
  final StreamController<dynamic> controller = StreamController<dynamic>();
  WebSocket(this.room);
  static Future<WebSocket> connect(String url) async => WebSocket(Uri.parse(url).pathSegments.last);
  StreamSubscription<dynamic> listen(void Function(dynamic)? onData, {Function? onError, void Function()? onDone, bool? cancelOnError}) => controller.stream.listen(onData,onError:onError,onDone:onDone,cancelOnError:cancelOnError);
  void add(dynamic value) { final data=jsonDecode(value as String); if(data['content'] != null) {final message=PreviewData.message(room,data['content']); controller.add(jsonEncode(message));} }
  Future close() => controller.close();
}
