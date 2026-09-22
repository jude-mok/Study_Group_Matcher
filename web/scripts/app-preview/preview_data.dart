import 'dart:convert';
import 'package:http/http.dart' as http;
class PreviewData {
  static final user=<String,dynamic>{'id':'alex','name':'Alex Chen','nyu_email':'alex@nyu.edu','nyu_id':'ac123','major':'Computer Science','minor':null,'academic_standing':2,'work_willingness':4,'preferred_location':'Bobst Library','time_preference':'Afternoon','avg_gpa':3.7};
  static final courses=<Map<String,dynamic>>[
    {'id':1,'course_code':'CSCI-UA 102','course_name':'Data Structures'},
    {'id':2,'course_code':'MATH-UA 123','course_name':'Calculus III'},
    {'id':3,'course_code':'CSCI-UA 310','course_name':'Basic Algorithms'}];
  static final enrolled=<Map<String,dynamic>>[{'user_id':'alex','course_id':1,'term':'Fall','year':2026,'created_at':now}];
  static String get now=>DateTime.now().toUtc().toIso8601String();
  static final groups=<Map<String,dynamic>>[
    {'id':'g0','course_id':1,'name':'Tuesday whiteboard sessions','max_members':5,'current_members':3,'location':'Bobst Library','admin_id':'alex','created_at':now},
    {'id':'g1','course_id':2,'name':'Calculus, together','max_members':5,'current_members':2,'location':'Courant','admin_id':'maya-demo-user','created_at':now},
    {'id':'g2','course_id':1,'name':'One problem at a time','max_members':6,'current_members':3,'location':'Bobst Library','admin_id':'sam-demo-user','created_at':now}];
  static final joined=<String>{'g0'};
  static final rooms=<Map<String,dynamic>>[{'id':'r0','group_id':'g0','name':'Tuesday whiteboard sessions','last_message_at':now}];
  static final messages=<Map<String,dynamic>>[{'id':'m0','room_id':'r0','sender_id':'maya-demo-user','content':'Ready to practice trees together?','created_at':now,'read_at':null}];
  static final proposals=<Map<String,dynamic>>[];
  static Map<String,dynamic> message(String room,String content) {final m=<String,dynamic>{'id':'m${messages.length}','room_id':room,'sender_id':'alex','content':content,'created_at':now,'read_at':null};messages.add(m);return m;}
  static http.Response request(String method,String path,Map<String,dynamic> body) {
    final uri=Uri.parse(path);final parts=uri.path.split('/').where((s)=>s.isNotEmpty).toList();
    final p='/'+parts.join('/');
    http.Response reply(dynamic data,[int status=200])=>http.Response(jsonEncode(data),status,headers:{'content-type':'application/json; charset=utf-8'});
    if(p.startsWith('/auth/')) return reply({'access_token':'demo','refresh_token':'demo','user':user},p.endsWith('signup')?201:200);
    if(p.startsWith('/users/')) {if(method=='PUT') user.addAll(body);if(method=='DELETE') return reply(null,204);return reply(parts.last=='me'||parts.last=='alex'?user:{...user,'id':parts.last,'name':parts.last=='maya-demo-user'?'Maya Patel':'Sam Lee'});}
    if(p=='/courses/search') return reply(courses.where((c)=>c['course_code'].toString().toLowerCase().contains((uri.queryParameters['course_code']??'').toLowerCase())).toList());
    if(p=='/courses') {if(method=='POST'){final c=<String,dynamic>{...body,'id':courses.length+1};courses.add(c);return reply(c,201);}return reply(courses);}
    if(p.startsWith('/courses/')) return reply(courses.firstWhere((c)=>c['id'].toString()==parts.last));
    if(p=='/user-courses') {if(method=='POST'){final e=<String,dynamic>{...body,'user_id':'alex','created_at':now};enrolled.add(e);return reply(e,201);}if(method=='DELETE'){enrolled.removeWhere((e)=>e['course_id'].toString()==uri.queryParameters['course_id']);return reply(null,204);}return reply(enrolled);}
    if(p=='/study-groups/recommend') return reply(groups.where((g)=>!joined.contains(g['id'])).map((g)=>{...g,'match_score':94.0,'score_breakdown':{'work_willingness':25.0,'gpa':24.0,'location':25.0,'time_preference':20.0}}).toList());
    if(p=='/study-groups/me') return reply(groups.where((g)=>joined.contains(g['id'])).toList());
    if(p.startsWith('/study-groups/course/')) return reply(groups.where((g)=>g['course_id'].toString()==parts.last).toList());
    if(p=='/study-groups'&&method=='POST'){final g=<String,dynamic>{...body,'id':'g${groups.length}','admin_id':'alex','created_at':now,'current_members':1};groups.add(g);joined.add(g['id']);return reply(g,201);}
    if(p.startsWith('/study-groups/')) {
      final id=parts[1];final group=groups.firstWhere((g)=>g['id']==id);
      if(parts.last=='join'){if(joined.add(id))group['current_members']++;return reply({'message':'Joined'},201);}
      if(parts.last=='leave'){if(joined.remove(id))group['current_members']--;return reply(null,204);}
      if(parts.last=='members')return reply([user,{...user,'id':'maya-demo-user','name':'Maya Patel'},{...user,'id':'sam-demo-user','name':'Sam Lee'}]);
      if(parts.contains('requests'))return reply([]);
      return reply(group);
    }
    if(p=='/rooms'){if(method=='POST'){final existing=rooms.where((r)=>r['group_id']==body['group_id']);if(existing.isNotEmpty)return reply(existing.first);final r=<String,dynamic>{'id':'r${rooms.length}',...body,'last_message_at':now};rooms.add(r);return reply(r,201);}return reply(rooms.where((r)=>joined.contains(r['group_id'])).toList());}
    if(p.startsWith('/rooms/')&&parts.last=='messages')return reply(uri.queryParameters.containsKey('before')?[]:messages.where((m)=>m['room_id']==parts[1]).toList());
    if(p=='/meetings/proposals'&&method=='POST'){final proposal=<String,dynamic>{...body,'id':'p${proposals.length}','proposed_by':'alex','expires_at':DateTime.now().add(const Duration(days:7)).toUtc().toIso8601String(),'is_confirmed':false,'attend_count':0,'total_members':3,'votes':<Map<String,dynamic>>[]};proposals.add(proposal);return reply(proposal,201);}
    if(p.startsWith('/meetings/proposals/'))return reply(proposals.where((v)=>v['room_id']==parts.last).toList());
    if(p=='/meetings/votes'){final proposal=proposals.firstWhere((p)=>p['id']==body['proposal_id']);final votes=proposal['votes'] as List;votes.removeWhere((v)=>v['user_id']=='alex');votes.add({'user_id':'alex','vote':body['vote']});proposal['attend_count']=votes.where((v)=>v['vote']==true).length;return reply(proposal);}
    return reply({'detail':'This action is not available in the sample demo.'},404);
  }
}
